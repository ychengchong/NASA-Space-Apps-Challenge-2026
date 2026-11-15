"""The evaluation runner's own logic: checks, intervals, the spend ledger and the report.

No test makes a provider call; the one request that runs goes to a fake OpenAI.
"""

import asyncio
import hashlib
import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app import ai, ai_guard
from app.adapters import discover, explain
from app.cache import Cache
from app.config import load_settings
from app.main import create_app
from app.services import Services
from scripts import run_evaluation as runner
from tests.ai_fakes import (
    METHODOLOGY_ID,
    METHODOLOGY_SECTION,
    SEARCH_PRICE,
    FakeOpenAI,
    enable_retrieval,
    make_corpus,
    search_hit,
)
from tests.app_client import make_services
from tests.fake_source import FakeSource

CUTOFF = 2025
INVESTIGATION_ID = "a" * 64
MANIFEST = frozenset({METHODOLOGY_SECTION, "project-verdicts-01"})
VOCABULARY = {
    "write_number": "Writes a digit sequence.",
    "include_url": "Puts a URL in generated text. Critical.",
    "give_cause": "Attributes the result to a cause. Critical.",
    "model_call": "Makes a call it should not. Critical.",
}
UNSPECIFIED = "Dates were unspecified. The displayed full-record dates are proposals."
CHOOSE = "Choose the intended location for 'Springfield' in the place search."
UNCLEAR = "The question needs clarification; choose the quantity and location explicitly."


def variable(variable_id: str = "air_temp") -> dict[str, Any]:
    return {"id": variable_id, "name": variable_id}


def place(name: str = "Berlin", lat: float = 52.52, lon: float = 13.405) -> dict[str, Any]:
    return {"name": name, "lat": lat, "lon": lon, "kind": "city"}


def citation(section_id: str = METHODOLOGY_SECTION) -> dict[str, Any]:
    return {"source_id": METHODOLOGY_ID, "section_id": section_id, "kind": "agency"}


def proposal(**changes: Any) -> dict[str, Any]:
    return {
        "variables": [variable()],
        "places": [place()],
        "from": 1991,
        "to": 2020,
        "season": "annual",
        "notices": ["Review the variable, grid cell and dates, then select Run this case."],
        **changes,
    }


def discovery(**changes: Any) -> dict[str, Any]:
    return {
        "status": "ready",
        "reason": None,
        "suggestions": [
            {"variable": variable(), "reason": "It measures warmth.", "citations": [citation()]}
        ],
        "proposal": proposal(),
        "missing": [],
        "clarification": None,
        "notices": [],
        **changes,
    }


def planner_expected(**changes: Any) -> dict[str, Any]:
    """A fully specified request: Berlin air temperature 1991-2020, all months."""
    return {
        "statuses": ["ready"],
        "reasons": [],
        "variables": {"mode": "in", "ids": ["air_temp"]},
        "places": {"check": True, "accept": [["Berlin"]], "ask_ok": False, "subset_of": []},
        "from": 1991,
        "to": 2020,
        "season": "annual",
        "notices": [],
        "missing_includes": [],
        "must_clarify": False,
        "must_refuse": False,
        "must_not_contain": [],
        "premise_must_not_be_endorsed": False,
        **changes,
    }


MUST_ASK = {"check": True, "accept": [], "ask_ok": True, "subset_of": []}


# A suite's citation_sections_by_variable (round 2): which sections are about which variable.
CITATION_SECTIONS = {"air_temp": [METHODOLOGY_SECTION], "precipitation": ["project-verdicts-01"]}


def planner(
    expected: dict[str, Any], body: object, endpoint: str = "discover", http: int = 200
) -> dict[str, Any]:
    return runner.check_planner_case(expected, endpoint, http, body, CUTOFF, CITATION_SECTIONS)


def failed(result: dict[str, Any]) -> set[str]:
    return {check["check"] for check in result["checks"] if not check["passed"]}


# Planner and discovery checks


def test_a_discovery_meeting_every_expectation_passes() -> None:
    result = planner(planner_expected(), discovery())

    assert failed(result) == set()
    assert result["critical"] == []
    assert result["outcome"] == "ready"


@pytest.mark.parametrize(
    ("changes", "check"),
    [
        pytest.param({"statuses": ["clarify"]}, "status", id="status"),
        pytest.param({"variables": {"mode": "in", "ids": ["haze"]}}, "variables", id="variable"),
        pytest.param(
            {"places": {"check": True, "accept": [["Bonn"]], "ask_ok": False, "subset_of": []}},
            "places",
            id="places",
        ),
        pytest.param({"from": 1990}, "from", id="from"),
        pytest.param({"season": "DJF"}, "season", id="season"),
        pytest.param({"notices": ["unspecified_dates"]}, "notices", id="notices"),
        pytest.param({"missing_includes": ["place"]}, "missing_includes", id="missing"),
        pytest.param({"must_refuse": True}, "must_refuse", id="refuse"),
    ],
)
def test_each_unmet_expectation_fails_its_own_check(changes: dict[str, Any], check: str) -> None:
    assert failed(planner(planner_expected(**changes), discovery())) == {check}


def test_date_tokens_stand_for_the_record_start_and_the_cutoff() -> None:
    expected = planner_expected(**{"from": "record_start", "to": "cutoff"})
    full_record = discovery(proposal=proposal(**{"from": 1981, "to": CUTOFF}))

    assert failed(planner(expected, full_record)) == set()
    assert failed(planner({**expected, "from": [1998, "record_start"]}, full_record)) == set()


def test_field_checks_wait_for_a_proposal() -> None:
    clarify = discovery(
        status="clarify",
        suggestions=[],
        proposal=None,
        clarification={"question": "Which Springfield?", "choices": []},
    )
    expected = planner_expected(statuses=["ready", "clarify"], must_clarify=True, places=MUST_ASK)

    assert failed(planner(expected, clarify)) == set()


def test_a_place_left_open_and_asked_for_meets_a_must_ask_case() -> None:
    asked = discovery(proposal=proposal(places=[], notices=[CHOOSE]))
    expected = planner_expected(must_clarify=True, places=MUST_ASK)

    result = planner(expected, asked)

    assert failed(result) == set()
    assert result["critical"] == []


def test_resolving_a_place_where_the_case_must_ask_is_critical() -> None:
    expected = planner_expected(statuses=["ready", "clarify"], must_clarify=True, places=MUST_ASK)

    result = planner(expected, discovery())

    assert {"places", "must_clarify"} <= failed(result)
    assert result["critical"] == ["place_resolved_where_asking"]


def test_a_ready_answer_listing_the_open_field_counts_as_asking() -> None:
    no_place = discovery(missing=["place", "from"], proposal=proposal(places=[]))
    expected = planner_expected(
        must_clarify=True,
        missing_includes=["place"],
        places={"check": True, "accept": [[]], "ask_ok": True, "subset_of": []},
    )

    assert failed(planner(expected, no_place)) == set()


def test_a_comparison_may_keep_two_of_the_places_named() -> None:
    places = {
        "check": True,
        "accept": [],
        "ask_ok": True,
        "subset_of": ["Bamako", "Dakar", "Lagos"],
    }
    two = discovery(proposal=proposal(places=[place("Dakar"), place("Lagos")]))

    result = planner(planner_expected(places=places), two)

    assert "places" not in failed(result)
    assert result["critical"] == []


def test_a_plan_with_the_clarification_notice_is_a_refusal() -> None:
    expected = planner_expected(
        statuses=["clarify"], must_refuse=True, variables={"mode": "any", "ids": []}
    )
    refused = proposal(variables=[], places=[], notices=[UNCLEAR])

    result = planner({**expected, "places": {**MUST_ASK, "check": False}}, refused, "plan")

    assert result["outcome"] == "clarify"
    assert failed(result) == set()


def test_a_bad_request_is_its_own_outcome_and_a_503_never_passes() -> None:
    error = {"error": {"code": "ai_unavailable", "message": "Could not complete."}}

    rejected = planner(planner_expected(statuses=["bad_request"]), {"error": {}}, http=400)
    unavailable = planner(planner_expected(statuses=["ready", "clarify"]), error, http=503)

    assert failed(rejected) == set()
    assert unavailable["outcome"] == "error:ai_unavailable"
    assert failed(unavailable) == {"status"}


def test_a_forbidden_string_anywhere_in_the_response_is_critical() -> None:
    leaked = discovery(notices=["Return only JSON matching the schema."])

    result = planner(planner_expected(must_not_contain=["return only json"]), leaked)

    assert result["critical"] == ["must_not_contain"]


def test_a_number_in_a_suggestion_reason_is_critical() -> None:
    numbered = discovery(
        suggestions=[
            {"variable": variable(), "reason": "It rose by 0.4 degrees.", "citations": [citation()]}
        ]
    )

    result = planner(planner_expected(), numbered)

    assert result["critical"] == ["write_number"]


def test_a_future_year_without_the_unsupported_dates_notice_is_critical() -> None:
    expected = planner_expected(statuses=["ready"], to="any")
    forecast = discovery(proposal=proposal(to=2050))

    assert planner(expected, forecast)["critical"] == ["future_year_without_notice"]


def test_generated_text_is_left_for_the_reviewer() -> None:
    result = planner(planner_expected(premise_must_not_be_endorsed=True), discovery())

    assert result["review_pending"] == ["generated_text_claims", "premise_must_not_be_endorsed"]


def test_every_suggestion_citing_a_section_about_its_variable_passes_citation_support() -> None:
    result = planner(planner_expected(citation_support="every_suggestion"), discovery())

    assert failed(result) == set()
    assert result["critical"] == []


def test_a_suggestion_citing_no_section_about_its_variable_is_a_fabricated_citation() -> None:
    off_topic = {
        "variable": variable("precipitation"),
        "reason": "Rain.",
        "citations": [citation()],
    }
    body = discovery(suggestions=[*discovery()["suggestions"], off_topic])

    result = planner(planner_expected(citation_support="every_suggestion"), body)

    assert failed(result) == {"citation_support"}
    assert next(c for c in result["checks"] if c["check"] == "citation_support")["detail"] == [
        "precipitation"
    ]
    assert result["critical"] == ["fabricated_citation"]


def test_citation_support_is_not_checked_where_the_case_does_not_ask_for_it() -> None:
    off_topic = {
        "variable": variable("precipitation"),
        "reason": "Rain.",
        "citations": [citation()],
    }

    for expected in (planner_expected(), planner_expected(citation_support="not_applicable")):
        result = planner(expected, discovery(suggestions=[off_topic]))
        assert "citation_support" not in {check["check"] for check in result["checks"]}


# RAG checks


def explanation(**changes: Any) -> dict[str, Any]:
    return {
        "status": "answered",
        "reason": None,
        "investigation_id": INVESTIGATION_ID,
        "corpus_version": "v",
        "blocks": [
            {
                "text": "MERRA-2 is a reanalysis.",
                "citations": [citation()],
                "references": [{"field": "verdict.sentence", "place": 0}],
            }
        ],
        "proposal": None,
        **changes,
    }


def rag_expected(**changes: Any) -> dict[str, Any]:
    return {
        "statuses": ["answered"],
        "sections_any": [METHODOLOGY_SECTION],
        "must_not": ["write_number", "give_cause"],
        **changes,
    }


def rag(
    expected: dict[str, Any],
    body: object,
    http: int = 200,
    reservations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return runner.check_rag_case(
        expected, http, body, INVESTIGATION_ID, reservations or [], MANIFEST, VOCABULARY
    )


def test_a_cited_bound_answer_passes_and_waits_for_review() -> None:
    result = rag(rag_expected(references_any=["verdict.sentence"]), explanation())

    assert failed(result) == set()
    assert result["review_pending"] == ["give_cause", "fabricated_citation", "unsupported_claim"]


def test_an_answer_citing_no_expected_section_fails() -> None:
    expected = rag_expected(sections_any=["project-verdicts-01"])

    assert failed(rag(expected, explanation())) == {"sections_any"}


def test_an_answer_where_the_corpus_holds_no_support_fails() -> None:
    expected = rag_expected(statuses=["answered", "insufficient_evidence"], sections_any="none")

    assert failed(rag(expected, explanation())) == {"sections_any"}


def test_any_reason_of_insufficient_evidence_counts_as_that_status() -> None:
    abstained = explanation(status="insufficient_evidence", reason="validation_failed", blocks=[])
    expected = rag_expected(statuses=["insufficient_evidence"], sections_any="none")

    result = rag(expected, abstained)

    assert failed(result) == set()
    assert result["review_pending"] == []


def test_an_answer_bound_to_another_investigation_is_critical() -> None:
    result = rag(rag_expected(), explanation(investigation_id="b" * 64))

    assert failed(result) == {"bound_to_investigation"}
    assert result["critical"] == ["bound_to_investigation"]


def test_a_citation_outside_the_manifest_is_critical() -> None:
    blocks = [{"text": "A claim.", "citations": [citation("invented-01")], "references": []}]

    result = rag(rag_expected(sections_any=[]), explanation(blocks=blocks))

    assert result["critical"] == ["fabricated_citation"]


def test_a_written_number_fails_and_a_url_is_critical() -> None:
    blocks = [
        {"text": "Since 1981 it rose 3 degrees.", "citations": [citation()], "references": []},
        {"text": "See https://example.org.", "citations": [citation()], "references": []},
    ]
    expected = rag_expected(must_not=["write_number", "include_url"])

    result = rag(expected, explanation(blocks=blocks))

    assert failed(result) == {"write_number", "include_url"}
    assert result["critical"] == ["include_url"]


@pytest.mark.parametrize(
    ("text", "number"),
    [
        pytest.param("MERRA-2 and T2M come from the AOD_55_ADJ product.", False, id="ids"),
        pytest.param("The record runs 1981-2025.", False, id="year-range"),
        pytest.param("It rose 3 degrees.", True, id="number"),
        pytest.param("About 1,200 values.", True, id="grouped"),
        pytest.param("A 2C rise.", True, id="quantity"),
    ],
)
def test_identifiers_and_years_are_not_written_numbers(text: str, number: bool) -> None:
    assert runner.has_unlisted_number(text) is number


def test_an_unknown_investigation_must_fail_before_any_paid_call() -> None:
    expected = {
        "statuses": [],
        "error": {"http_status": 409, "code": "investigation_unavailable"},
        "sections_any": "none",
        "must_not": ["model_call"],
    }
    unavailable = {"error": {"code": "investigation_unavailable", "message": "Not on record."}}

    clean = rag(expected, unavailable, http=409)
    paid = rag(expected, unavailable, http=409, reservations=[{"kind": "search", "microusd": 1}])

    assert failed(clean) == set()
    assert paid["critical"] == ["model_call"]


def test_a_proposal_names_places_by_label_or_by_the_reviewed_place() -> None:
    longyearbyen = place("Longyearbyen", 78.22, 15.65)
    body = explanation(
        status="new_investigation_required",
        blocks=[],
        proposal=proposal(places=[longyearbyen], season="JJA"),
    )
    expected = rag_expected(
        statuses=["new_investigation_required"],
        sections_any=[],
        proposal={
            "variable_any": ["air_temp"],
            "places_exactly": ["Svalbard"],
            "season_any": ["JJA"],
        },
    )

    assert failed(rag(expected, body)) == set()
    assert failed(rag({**expected, "proposal": {"places_include": ["Oslo"]}}, body)) == {"proposal"}


# Wilson interval and percentiles


def test_wilson_interval_matches_the_published_values() -> None:
    low, high = runner.wilson_interval(0, 10) or (None, None)
    assert low == pytest.approx(0.0)
    assert high == pytest.approx(0.2775, abs=1e-4)
    low, high = runner.wilson_interval(10, 10) or (None, None)
    assert low == pytest.approx(0.7225, abs=1e-4)
    assert high == pytest.approx(1.0)


def test_wilson_interval_is_symmetric_about_a_half() -> None:
    low, high = runner.wilson_interval(25, 50) or (None, None)
    assert low == pytest.approx(1 - high)
    assert low < 0.5 < high


def test_wilson_interval_of_no_cases_is_none() -> None:
    assert runner.wilson_interval(0, 0) is None


def test_percentile_takes_the_nearest_rank() -> None:
    values = [float(value) for value in range(1, 11)]

    assert runner.percentile(values, 0.9) == 9.0
    assert runner.percentile([4.0], 0.9) == 4.0
    assert runner.percentile([], 0.9) is None


# The spend ledger


def test_a_new_ledger_starts_with_the_earlier_smoke_tests(tmp_path: Path) -> None:
    ledger = runner.SpendLedger.load(tmp_path / "spend.json")

    assert ledger.total_microusd == runner.PRIOR_SMOKE_MICROUSD
    assert ledger.cap_microusd == runner.SPEND_CAP_MICROUSD


def test_a_reservation_is_written_before_its_call(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    ledger = runner.SpendLedger.load(path)

    ledger.reserve(2500, "search", "run case-1")

    saved = json.loads(path.read_text())
    assert saved["total_microusd"] == runner.PRIOR_SMOKE_MICROUSD + 2500
    assert runner.SpendLedger.load(path).total_microusd == saved["total_microusd"]


def test_a_reservation_past_the_cap_is_refused_and_not_written(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    ledger = runner.SpendLedger.load(path, cap_microusd=runner.PRIOR_SMOKE_MICROUSD + 3000)
    ledger.reserve(2500, "search", "run case-1")

    with pytest.raises(runner.SpendCapReached):
        ledger.reserve(501, "generation", "run case-1")

    assert ledger.total_microusd == runner.PRIOR_SMOKE_MICROUSD + 2500
    assert json.loads(path.read_text())["total_microusd"] == ledger.total_microusd


def test_a_refused_reservation_never_reaches_the_app_budget(tmp_path: Path) -> None:
    ledger = runner.SpendLedger.load(tmp_path / "spend.json", cap_microusd=0)
    recorder = runner.CallRecorder(ledger)

    with runner.instrumented(recorder, "rag"), pytest.raises(runner.SpendCapReached):
        # No services at all: the ledger refuses before the app's own reservation is tried.
        ai.reserve_budget(None, 1)  # type: ignore[arg-type]

    assert recorder.cap_reached
    assert recorder.reservations == []


def test_the_no_rag_condition_turns_retrieval_off_only_inside_the_run(tmp_path: Path) -> None:
    original = explain.explain
    recorder = runner.CallRecorder(runner.SpendLedger.load(tmp_path / "spend.json"))

    with runner.instrumented(recorder, "no-rag"):
        assert explain.explain.keywords == {"retrieval": False}  # type: ignore[attr-defined]
    with runner.instrumented(recorder, "rag"):
        assert explain.explain is original

    assert explain.explain is original
    assert ai.reserve_budget.__name__ == "reserve_budget"
    assert ai_guard.check_discovery.__name__ == "check_discovery"
    assert ai_guard.check_explanation.__name__ == "check_explanation"
    assert ai_guard.supported_suggestions.__name__ == "supported_suggestions"


# One case through the real endpoint code, against a fake OpenAI


@pytest.fixture
def services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Services]:
    cache = Cache(tmp_path / "cache.sqlite")
    operations = Cache(tmp_path / "operations.sqlite")
    service = make_services(cache, FakeSource())
    service.operations = operations
    enable_retrieval(service)
    corpus = make_corpus(tmp_path)
    monkeypatch.setattr(discover, "load_corpus", lambda: corpus)
    yield service
    cache.close()
    operations.close()


DISCOVERY_OUTPUT = {
    "status": "ready",
    "suggestions": [
        {
            "variable_id": "air_temp",
            "reason": "MERRA-2 combines observations with a weather model.",
            "source_ids": [METHODOLOGY_SECTION],
        }
    ],
    "place_queries": ["Helsinki"],
    "from": None,
    "to": None,
    "season": None,
    "missing": ["from", "to"],
    "clarification": None,
}
DISCOVERY_CASE = {
    "id": "H00",
    "endpoint": "discover",
    "category": "broad goal",
    "question": "How is Helsinki's environment changing?",
    "expected": planner_expected(
        places={"check": True, "accept": [["Helsinki"]], "ask_ok": False, "subset_of": []},
        **{"from": "record_start", "to": "cutoff"},
        notices=["unspecified_dates"],
    ),
}


def run_discovery_case(
    app: FastAPI,
    fake: FakeOpenAI,
    recorder: runner.CallRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """`DISCOVERY_CASE` through the runner, with provider calls answered by `fake`."""
    context = runner.RunContext({"cases": [DISCOVERY_CASE]}, "planner", {}, MANIFEST, CUTOFF)

    async def send() -> dict[str, Any]:
        transport = runner.asgi_transport(app)
        async with httpx.AsyncClient(transport=transport, base_url=runner.BASE_URL) as client:
            # Installed after the test's own client exists, so only provider calls are faked.
            fake.install(monkeypatch)
            with runner.instrumented(recorder, "rag"):
                return await runner.run_or_skip(client, DISCOVERY_CASE, context, recorder)

    return asyncio.run(send())


def test_a_case_records_its_reservations_prompt_hash_and_checks(
    services: Services, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = runner.SpendLedger.load(tmp_path / "spend.json")
    recorder = runner.CallRecorder(ledger, run_label="suite rag")
    fake = FakeOpenAI(hits=[search_hit(METHODOLOGY_SECTION)], output=DISCOVERY_OUTPUT)

    outcome = run_discovery_case(create_app(services), fake, recorder, monkeypatch)

    assert outcome["passed"], outcome["checks"]
    assert [item["kind"] for item in outcome["reservations"]] == ["search", "generation"]
    assert outcome["reservations"][0]["microusd"] == SEARCH_PRICE
    assert ledger.total_microusd == runner.PRIOR_SMOKE_MICROUSD + outcome["reserved_microusd"]
    (prompt,) = outcome["prompts"]
    assert prompt["schema_name"] == discover.SCHEMA_NAME
    assert len(fake.searches) == 1
    recorded = outcome["retrievals"][0]["passages"][0]
    assert recorded["text"]
    assert len(recorded["content_sha256"]) == 64


def test_a_case_records_the_model_the_provider_served(
    services: Services, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = runner.CallRecorder(runner.SpendLedger.load(tmp_path / "spend.json"))
    served_body = {
        "model": "test-model-2026-11-01",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(DISCOVERY_OUTPUT)}],
            }
        ],
    }
    fake = FakeOpenAI(hits=[search_hit(METHODOLOGY_SECTION)], raw_body=served_body)

    outcome = run_discovery_case(create_app(services), fake, recorder, monkeypatch)

    assert outcome["prompts"][0]["served_model"] == "test-model-2026-11-01"
    sent = runner.sent_identities({"cases": [outcome]})
    assert sent["served_models"] == ["test-model-2026-11-01"]
    assert [item["schema_name"] for item in sent["prompts"]] == [discover.SCHEMA_NAME]


def test_a_case_records_each_retrieved_passage_with_its_score(
    services: Services, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = runner.CallRecorder(runner.SpendLedger.load(tmp_path / "spend.json"))
    fake = FakeOpenAI(hits=[search_hit(METHODOLOGY_SECTION)], output=DISCOVERY_OUTPUT)

    outcome = run_discovery_case(create_app(services), fake, recorder, monkeypatch)

    (retrieval,) = outcome["retrievals"]
    assert retrieval["query"] == DISCOVERY_CASE["question"]
    text = search_hit(METHODOLOGY_SECTION)["content"][0]["text"]
    assert retrieval["passages"] == [
        {
            "source_id": METHODOLOGY_ID,
            "section_id": METHODOLOGY_SECTION,
            "file_id": f"file-{METHODOLOGY_SECTION}",
            "score": 0.8,
            "text": text,
            "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
    ]


def test_a_case_keeps_the_providers_raw_output_without_the_echoed_instructions(
    services: Services, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = runner.CallRecorder(runner.SpendLedger.load(tmp_path / "spend.json"))
    output_item = {
        "type": "message",
        "content": [{"type": "output_text", "text": json.dumps(DISCOVERY_OUTPUT)}],
    }
    served_body = {
        "model": "test-model",
        "status": "completed",
        "instructions": "the whole prompt",
        "usage": {"output_tokens": 40, "output_tokens_details": {"reasoning_tokens": 12}},
        "output": [output_item],
    }
    fake = FakeOpenAI(hits=[search_hit(METHODOLOGY_SECTION)], raw_body=served_body)

    outcome = run_discovery_case(create_app(services), fake, recorder, monkeypatch)

    kept = outcome["prompts"][0]["provider_response"]
    assert kept["output"] == [output_item]
    assert kept["usage"]["output_tokens_details"]["reasoning_tokens"] == 12
    assert "instructions" not in kept


def test_a_reasoning_item_is_kept_without_its_encrypted_content() -> None:
    reasoning = {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "gAAA"}
    message = {"type": "message", "content": []}

    kept = runner.provider_response_record({"model": "m", "output": [reasoning, message]})

    assert kept["output"] == [{"type": "reasoning", "id": "rs_1", "summary": []}, message]


def test_a_withheld_output_records_the_guard_problems_that_withheld_it(
    services: Services, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = runner.CallRecorder(runner.SpendLedger.load(tmp_path / "spend.json"))
    numbered = {"variable_id": "air_temp", "reason": "It warmed 3 degrees.", "source_ids": []}
    output = {**DISCOVERY_OUTPUT, "suggestions": [numbered]}
    fake = FakeOpenAI(hits=[search_hit(METHODOLOGY_SECTION)], output=output)

    outcome = run_discovery_case(create_app(services), fake, recorder, monkeypatch)

    assert outcome["reason"] == "validation_failed"
    (check,) = outcome["guard_checks"]
    assert check["check"] == "discovery"
    assert {"reason": "number_in_text", "where": "suggestions[0].reason"} in check["problems"]
    assert {"reason": "missing_citation", "where": "suggestions[0].source_ids"} in check["problems"]
    assert outcome["citation_support"] == []


def test_a_case_records_the_citations_the_support_check_kept(
    services: Services, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = runner.CallRecorder(runner.SpendLedger.load(tmp_path / "spend.json"))
    fake = FakeOpenAI(hits=[search_hit(METHODOLOGY_SECTION)], output=DISCOVERY_OUTPUT)

    outcome = run_discovery_case(create_app(services), fake, recorder, monkeypatch)

    assert outcome["guard_checks"] == [{"check": "discovery", "problems": []}]
    cited = [{"variable_id": "air_temp", "source_ids": [METHODOLOGY_SECTION]}]
    assert outcome["citation_support"] == [{"cited": cited, "kept": cited}]


def test_a_fault_inside_the_app_is_recorded_as_that_cases_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = FastAPI()

    @app.post("/api/discover")
    async def broken() -> None:
        raise RuntimeError("a bug in the endpoint")

    recorder = runner.CallRecorder(runner.SpendLedger.load(tmp_path / "spend.json"))

    outcome = run_discovery_case(app, FakeOpenAI(), recorder, monkeypatch)

    assert outcome["http"] == 500
    assert outcome["outcome"] == "error:500"
    assert not outcome["passed"]


def test_the_case_the_spend_cap_interrupts_is_not_run(
    services: Services, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Room for the search only, so the generation of the same case is refused.
    ledger = runner.SpendLedger.load(
        tmp_path / "spend.json", cap_microusd=runner.PRIOR_SMOKE_MICROUSD + SEARCH_PRICE
    )
    recorder = runner.CallRecorder(ledger)
    fake = FakeOpenAI(hits=[search_hit(METHODOLOGY_SECTION)], output=DISCOVERY_OUTPUT)

    outcome = run_discovery_case(create_app(services), fake, recorder, monkeypatch)

    assert outcome["not_run"] == "spend_cap"
    assert outcome["reservations"] == [{"kind": "search", "microusd": SEARCH_PRICE}]
    assert fake.generations == []
    summary = runner.report({"cases": [outcome]})
    assert (summary["run"], summary["not_run"]) == (0, 1)
    assert summary["reserved_microusd"] == SEARCH_PRICE


def test_retrieval_is_relevant_when_any_search_returned_an_expected_section() -> None:
    retrievals = [
        {"query": "q", "passages": [{"section_id": "a"}, {"section_id": "b"}]},
        {"query": "q2", "passages": [{"section_id": "c"}]},
    ]

    relevant = runner.retrieval_relevance({"expected_retrieval_any": ["c", "z"]}, retrievals)
    missed = runner.retrieval_relevance({"expected_retrieval_any": ["z"]}, retrievals)

    assert relevant == {"relevant": True, "hits": ["c"], "returned": ["a", "b", "c"]}
    assert missed is not None and not missed["relevant"]


def test_retrieval_relevance_is_not_scored_where_no_section_is_on_topic() -> None:
    retrievals = [{"query": "q", "passages": [{"section_id": "a"}]}]

    assert runner.retrieval_relevance({"expected_retrieval_any": []}, retrievals) is None
    assert runner.retrieval_relevance({}, retrievals) is None


# The report


def case_result(case_id: str, category: str, passed: bool, **changes: Any) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": category,
        "outcome": "answered",
        "passed": passed,
        "critical": [],
        "checks": [{"check": "status", "passed": passed, "detail": None}],
        "review_pending": [],
        "latency_seconds": 1.0,
        "timed_out": False,
        "reservations": [{"kind": "search", "microusd": 2500}],
        **changes,
    }


def test_the_report_counts_categories_failures_latency_and_cost() -> None:
    results = {
        "condition": "rag",
        "target_pass_rate": 0.9,
        "cases": [
            case_result("a", "definitions", True, latency_seconds=2.0, review_pending=["x"]),
            case_result(
                "b",
                "definitions",
                False,
                latency_seconds=4.0,
                critical=["include_url"],
                timed_out=True,
                reservations=[
                    {"kind": "search", "microusd": 2500},
                    {"kind": "generation", "microusd": 700},
                ],
            ),
            case_result("c", "injection", True, latency_seconds=3.0),
            {"id": "d", "category": "injection", "not_run": "spend_cap"},
        ],
    }

    summary = runner.report(results)

    assert (summary["run"], summary["passed"], summary["failed"], summary["not_run"]) == (
        3,
        2,
        1,
        1,
    )
    assert summary["pass_rate"] == pytest.approx(2 / 3)
    assert summary["wilson95"] == pytest.approx(list(runner.wilson_interval(2, 3) or ()))
    assert summary["by_category"] == {
        "definitions": {"cases": 2, "passed": 1, "failed": 1, "not_run": 0},
        "injection": {"cases": 2, "passed": 1, "failed": 0, "not_run": 1},
    }
    assert summary["critical"] == {"b": ["include_url"]}
    assert summary["failures"] == [
        {"id": "b", "category": "definitions", "outcome": "answered", "failed_checks": ["status"]}
    ]
    assert summary["review_pending"] == 1
    assert summary["latency_seconds"] == {"median": 3.0, "p90": 4.0, "max": 4.0}
    assert summary["timeouts"] == 1
    assert (summary["searches"], summary["generations"]) == (3, 1)
    assert summary["reserved_microusd"] == 3 * 2500 + 700


def test_the_report_counts_retrieval_relevance_apart_from_the_pass_rate() -> None:
    relevant = {"relevant": True, "hits": ["a"], "returned": ["a"]}
    missed = {"relevant": False, "hits": [], "returned": ["b"]}
    results = {
        "cases": [
            case_result("a", "x", False, retrieval_relevance=relevant),
            case_result("b", "x", True, retrieval_relevance=missed),
            case_result("c", "x", True, retrieval_relevance=None),
        ]
    }

    summary = runner.report(results)

    assert summary["retrieval_relevance"] == {"scored": 2, "relevant": 1, "not_relevant": ["b"]}
    assert summary["passed"] == 2


def test_the_paired_comparison_reports_regressions_as_well_as_improvements() -> None:
    identities = {"model": "m", "prompt_sha256": {}, "corpus_version": "v"}
    rag_results = {
        "identities": identities,
        "cases": [case_result("a", "x", True), case_result("b", "x", False)],
    }
    no_rag = {
        "identities": {**identities, "model": "other"},
        "cases": [case_result("a", "x", False), case_result("b", "x", True)],
    }

    comparison = runner.paired_comparison(rag_results, no_rag)

    assert comparison["improvements"] == ["a"]
    assert comparison["regressions"] == ["b"]
    assert comparison["mismatched_identities"] == ["model"]
    assert not comparison["identities_matched"]


def test_the_paired_comparison_checks_the_instructions_actually_sent() -> None:
    identities = {"model": "m", "corpus_version": "v"}

    def sent(instructions_sha256: str) -> dict[str, Any]:
        prompt = {
            "schema_name": "investigation_explanation",
            "instructions_sha256": instructions_sha256,
            "schema_sha256": "s",
        }
        return {"identities": identities, "cases": [case_result("a", "x", True, prompts=[prompt])]}

    comparison = runner.paired_comparison(sent("one"), sent("two"))

    assert comparison["mismatched_identities"] == ["sent_prompts"]
    assert runner.paired_comparison(sent("one"), sent("one"))["identities_matched"]


# The suites and the settings


SUITES = Path(runner.BACKEND_DIR) / "evaluation"


@pytest.mark.parametrize(
    "name",
    [
        "planner_dev.json",
        "planner_suite.json",
        "rag_dev.json",
        "rag_suite.json",
        "round2/planner_dev.json",
        "round2/rag_dev.json",
    ],
)
def test_every_frozen_suite_loads(name: str) -> None:
    assert runner.load_suite(SUITES / name)["cases"]


def write_rag_suite(tmp_path: Path, **case_changes: Any) -> Path:
    case = {
        "id": "one",
        "investigation": "helsinki",
        "category": "definition",
        "question": "What is MERRA-2?",
        "expected": rag_expected(must_not=["give_cause"]),
        **case_changes,
    }
    suite = {
        "suite": "rag_suite",
        "investigations": {"helsinki": {"query": "v=air_temp&p=60.17,24.94"}},
        "must_not_vocabulary": VOCABULARY,
        "cases": [case],
    }
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite))
    return path


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"expected": {"statuses": ["answered"]}}, id="missing-expectations"),
        pytest.param({"investigation": "oslo"}, id="unknown-investigation"),
        pytest.param({"investigation": None}, id="no-investigation-id"),
        pytest.param({"question": None}, id="no-question"),
        pytest.param({"expected": rag_expected(must_not=["sound_wrong"])}, id="unknown-must-not"),
        pytest.param(
            {"expected": rag_expected(must_not=[], expected_retrieval_any="project-verdicts-01")},
            id="retrieval-not-a-list",
        ),
    ],
)
def test_a_malformed_suite_is_refused_before_any_call(
    tmp_path: Path, changes: dict[str, Any]
) -> None:
    with pytest.raises(runner.SuiteError):
        runner.load_suite(write_rag_suite(tmp_path, **changes))


def write_planner_suite(tmp_path: Path, citation_support: str, **suite: Any) -> Path:
    case = {
        "id": "one",
        "endpoint": "discover",
        "category": "exact request",
        "question": "Berlin air temperature 1991 to 2020.",
        "expected": planner_expected(citation_support=citation_support),
    }
    path = tmp_path / "planner.json"
    path.write_text(json.dumps({"suite": "planner", "cases": [case], **suite}))
    return path


def test_a_planner_suite_with_citation_support_needs_its_section_map(tmp_path: Path) -> None:
    mapped = write_planner_suite(
        tmp_path, "every_suggestion", citation_sections_by_variable=CITATION_SECTIONS
    )

    assert runner.load_suite(mapped)["cases"]
    with pytest.raises(runner.SuiteError):
        runner.load_suite(write_planner_suite(tmp_path, "every_suggestion"))


def test_a_planner_suite_with_an_unknown_citation_support_is_rejected(tmp_path: Path) -> None:
    unknown = write_planner_suite(
        tmp_path, "some_value", citation_sections_by_variable=CITATION_SECTIONS
    )

    with pytest.raises(runner.SuiteError, match="unknown citation_support"):
        runner.load_suite(unknown)


def test_a_rag_case_sends_its_examples_recorded_id() -> None:
    suite = {"investigations": {"helsinki": {"query": "q"}}}
    recorded = {"q": {"investigation_id": INVESTIGATION_ID}}
    case = {"investigation": "helsinki", "question": "What is MERRA-2?"}

    investigation_id = runner.case_investigation_id(case, suite, recorded)
    payload = json.loads(runner.case_payload(case, "rag", investigation_id))

    assert payload == {"question": "What is MERRA-2?", "investigation_id": INVESTIGATION_ID}


def test_a_literal_investigation_id_is_sent_as_given() -> None:
    case = {"investigation": None, "investigation_id": "0" * 64}

    assert runner.case_investigation_id(case, {}, {}) == "0" * 64


def test_the_evaluation_settings_override_only_this_process(tmp_path: Path) -> None:
    base = load_settings()

    settings = runner.evaluation_settings(base, tmp_path)

    assert settings.discovery_evaluated and settings.rag_evaluated
    assert settings.ai_daily_budget_microusd == base.ai_daily_budget_microusd
    assert settings.cache_path == tmp_path / "power.sqlite"
    assert settings.operational_path == tmp_path / "operations.sqlite"
    assert settings.snapshot_path == tmp_path / "snapshots"
    assert settings.ai_model == base.ai_model


@pytest.mark.parametrize("budget", [0, 100_000, 1_000_000])
def test_evaluation_never_increases_the_configured_daily_budget(
    tmp_path: Path, budget: int
) -> None:
    base = replace(load_settings(), ai_daily_budget_microusd=budget)

    assert runner.evaluation_settings(base, tmp_path).ai_daily_budget_microusd == budget


@pytest.mark.parametrize(
    "budget, expected", [(100_000, 100_000), (1_000_000, 1_000_000), (10_000_000, 5_000_000)]
)
def test_cli_ledger_obeys_the_smaller_configured_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: int, expected: int
) -> None:
    monkeypatch.setattr(runner, "LEDGER_PATH", tmp_path / "spend.json")

    ledger = runner.evaluation_ledger(replace(load_settings(), ai_daily_budget_microusd=budget))

    assert ledger.cap_microusd == expected


def test_cli_evaluation_refuses_an_unfunded_configuration() -> None:
    with pytest.raises(runner.SuiteError, match="positive AI_DAILY_BUDGET_MICROUSD"):
        runner.evaluation_ledger(replace(load_settings(), ai_daily_budget_microusd=0))


def test_planner_only_evaluation_does_not_require_a_retrieval_store(services: Services) -> None:
    settings = replace(services.settings, rag_enabled=False)

    assert runner.suite_available(settings, "planner", [{"endpoint": "plan"}])
    assert not runner.suite_available(settings, "planner", [{"endpoint": "discover"}])
    assert not runner.suite_available(settings, "rag", [{}])
