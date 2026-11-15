"""Run a frozen evaluation suite through the real endpoint code with real OpenAI (spec 12).

The runner builds the whole FastAPI app in this process and sends every case through it with
httpx's ASGI transport, so each request takes the code path a browser's request takes: the
body bound, validation, the generation slot, retrieval, generation and the server's checks.
Each case is sent once; nothing is retried. Per case it records the request, the HTTP status,
the response's status and reason, a summary of the body, the latency, the reserved cost, the
automated checks against the case's `expected` object, and what is left for the reviewer.
From inside the app process it also records, without changing what the app returns or logs,
every passage each search returned with its score, the provider's response bodies (raw output
and token usage), the guard problems of every check of a provider output, and the citations
the discovery support check kept.

Run from backend/, with the key loaded from ../.env and never printed:

    env -u AI_MODEL UV_PYTHON=3.14 uv run --env-file ../.env python -m scripts.run_evaluation \\
        --suite evaluation/rag_suite.json --condition rag --state-dir <scratch dir> \\
        --out <results.json>

`--condition no-rag` (RAG suites only) runs the same explanation cases with no retrieval: the
explanation adapter's internal `retrieval=False` parameter skips the vector search and gives
the model no passages, with the same instructions, schema and checks. `--limit N` runs the
first N cases. `--report RESULTS [--compare NO_RAG_RESULTS]` prints the report of a results
file, and the paired RAG/no-RAG comparison, without any call.

Settings come from the environment, with these overrides for this process only: discovery
and explanations count as evaluated (that is what is being measured), the configured daily
budget is preserved, the rate limits allow a sequential run, and the cache, operations
database and snapshots live in `--state-dir`. The cache there starts as a copy of the
repository's state/power.sqlite, or of the shipped seed when there is none.

Spend: the historical maximum is USD 5 for all evaluation runs together. The CLI uses the
smaller of that maximum and AI_DAILY_BUDGET_MICROUSD as its cumulative ledger cap; it
never increases a configured daily allowance. The ledger at
state/evaluation-spend.json (operational state, not committed) holds every reservation of
every run, starting with USD 0.15 for the earlier smoke tests. Before each paid call (a search
or a generation) the runner adds the call's reserved upper bound, which `app.ai` computes,
and refuses to start a call that would take the total past that cap; the ledger is written at
once, so a call that crashes still counts. A refusal ends the run: the case it interrupts and
the remaining cases are recorded as not run, outside the pass rate, and the interrupted case
keeps the reservations it made. The reserved cost is an upper bound, not the provider's billed
usage.

Identities: `identities` freezes the configuration before the first call, including the model
name the settings request. What was actually sent and served is recorded per generation (the
hashes of the instructions and schema sent, and the `model` field of the provider's response)
and collected for the run by `sent_identities`.

Suites: the planner/discovery format is described in backend/evaluation/README.md and the
RAG format in the `scoring_notes` of backend/evaluation/rag_suite.json; `check_planner_case`
and `check_rag_case` implement them. The round-2 additions (backend/evaluation/round2/README.md)
are read too: a planner case's `expected.citation_support` is checked against the suite's
`citation_sections_by_variable`, and a RAG case's `expected.expected_retrieval_any` scores
retrieval relevance apart from the pass result. A case passes when every automated check
passes. Checks that need reading the text (a premise endorsed, a cause or forecast claimed, an
answer the cited passages do not support) cannot be automated: they are listed per case under
`review_pending` for the reviewer pass, which an AI may do only if the results say so.
"""

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI

from app import ai, ai_guard
from app.adapters import discover as discover_adapter
from app.adapters import explain as explain_adapter
from app.adapters.planner import resolve_place_query
from app.adapters.rest import load_examples
from app.catalogue import load_catalogue
from app.config import BACKEND_DIR, DATA_DIR, Settings, load_settings
from app.corpus import Corpus, load_corpus
from app.errors import RateLimitedError
from app.main import create_app
from app.models import MAX_PASSAGES, ExtractedPlan, RetrievedPassage
from app.services import Services, build_services, close_services

REPO_DIR = BACKEND_DIR.parent
LEDGER_PATH = REPO_DIR / "state" / "evaluation-spend.json"
STATE_CACHE = REPO_DIR / "state" / "power.sqlite"
SEED_CACHE = DATA_DIR / "cache.sqlite"

# The owner-approved hard cap for all evaluation runs together, and what the earlier smoke
# tests are counted as, in microdollars.
SPEND_CAP_MICROUSD = 5_000_000
PRIOR_SMOKE_MICROUSD = 150_000
MICROUSD_PER_USD = 1_000_000
# Rate limits allow a sequential suite; the configured budget is never overridden.
EVALUATION_RATE_PER_MINUTE = 100_000
# Spec 12: the predeclared pass target, used when a suite's header does not state its own.
SPEC_TARGET_PASS_RATE = 0.9
# The endpoints keep their own 30-second deadline; this outer bound only guards the runner.
RUNNER_TIMEOUT_SECONDS = ai.DEADLINE_SECONDS + 15
GIT_TIMEOUT_SECONDS = 10
# The 97.5th percentile of the standard normal distribution: a two-sided 95% interval.
WILSON_Z_95 = 1.959963984540054
LATENCY_PERCENTILE = 0.9
BASE_URL = "http://evaluation.local"

SuiteKind = Literal["planner", "rag"]
Condition = Literal["rag", "no-rag"]
CallKind = Literal["search", "generation"]

ENDPOINT_PATHS = {"discover": "/api/discover", "plan": "/api/plan", "explain": "/api/explain"}
# backend/evaluation/README.md: a notice key matches a proposal notice by its start.
NOTICE_PREFIXES = {
    "unspecified_dates": "Dates were unspecified.",
    "unsupported_dates": "Requested dates are unsupported.",
    "choose_place": "Choose the intended location for",
    "needs_clarification": "The question needs clarification",
}
PLANNER_EXPECTED_KEYS = frozenset(
    {
        "statuses",
        "reasons",
        "variables",
        "places",
        "from",
        "to",
        "season",
        "notices",
        "missing_includes",
        "must_clarify",
        "must_refuse",
        "must_not_contain",
        "premise_must_not_be_endorsed",
    }
)
RAG_EXPECTED_KEYS = frozenset({"statuses", "sections_any", "must_not"})
# The held-out RAG suite, whose must_not vocabulary the development suite shares.
RAG_SUITE_FILE = "rag_suite.json"
# Settings without a default: a discover "ready" that lists one as missing asks the user.
CHOOSABLE_FIELDS = ("variable", "place")
# Round 2 (backend/evaluation/round2/README.md): every suggestion must cite a section about its
# own variable, or the case does not ask for that check.
CITATION_SUPPORT_VALUES = frozenset({"every_suggestion", "not_applicable"})
# Checks that are critical errors whatever a suite's vocabulary says.
ALWAYS_CRITICAL = frozenset({"bound_to_investigation", "fabricated_citation"})
CRITICAL_MARK = "Critical."
# As app.ai_guard reads text: a token with a digit is a number unless it is a year, a range
# of years, or an identifier that starts with a letter, such as MERRA-2 or T2M.
_TOKEN = re.compile(r"\w+(?:[-.,/'\u2019]\w+)*")
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:-[A-Za-z0-9]+)*")
_YEARS = re.compile(r"(?:19|20)[0-9]{2}(?:[-/](?:19|20)[0-9]{2})?")
_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_SECRET = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
# The parts of a Responses body kept per generation: what was served, how it ended, the token
# usage (hidden reasoning included) and the raw output. The echoed instructions and schema
# are left out; their hashes are recorded instead. No body holds a credential.
PROVIDER_RESPONSE_KEYS = (
    "model",
    "status",
    "incomplete_details",
    "error",
    "reasoning",
    "max_output_tokens",
    "usage",
    "output",
)


class SuiteError(ValueError):
    """The suite file is malformed or does not fit this environment; nothing is sent."""


class SpendCapReached(RateLimitedError):
    """A paid call would take the evaluation ledger past its cap, so it was not started."""


# The spend ledger


@dataclass
class SpendLedger:
    """Every reservation of every evaluation run, in microdollars, kept in one JSON file."""

    path: Path
    cap_microusd: int
    entries: list[dict[str, Any]]

    @classmethod
    def load(cls, path: Path, cap_microusd: int = SPEND_CAP_MICROUSD) -> "SpendLedger":
        """The ledger at `path`; a new one holding only the prior smoke-test entry when the
        file does not exist yet.
        """
        if path.exists():
            entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
        else:
            entries = [
                {
                    "at": _now(),
                    "label": "earlier live smoke tests",
                    "kind": "prior",
                    "microusd": PRIOR_SMOKE_MICROUSD,
                }
            ]
        return cls(path=path, cap_microusd=cap_microusd, entries=entries)

    @property
    def total_microusd(self) -> int:
        return sum(int(entry["microusd"]) for entry in self.entries)

    def reserve(self, amount_microusd: int, kind: str, label: str) -> None:
        """Add one reservation and write the ledger, before the call it pays for starts.

        Raises `SpendCapReached`, and writes nothing, when the total would pass the cap.
        """
        if self.total_microusd + amount_microusd > self.cap_microusd:
            raise SpendCapReached(
                "The evaluation spend cap would be exceeded, so the call was not started."
            )
        self.entries.append(
            {"at": _now(), "label": label, "kind": kind, "microusd": amount_microusd}
        )
        self.save()

    def save(self) -> None:
        _write_json(
            self.path,
            {
                "cap_microusd": self.cap_microusd,
                "total_microusd": self.total_microusd,
                "entries": self.entries,
            },
        )


@dataclass
class CallRecorder:
    """What the case being run did inside the app: the reservations of its paid calls; per
    generation the hashes of the instructions and schema sent, the model the provider reports
    it served and the provider's response body; per search every passage returned, with its
    score; the guard problems of every check of a provider output; and the citations the
    discovery support check kept. `cap_reached` stays set once the ledger refuses a call.
    """

    ledger: SpendLedger
    run_label: str = ""
    case_id: str = ""
    kind: CallKind = "generation"
    reservations: list[dict[str, Any]] = field(default_factory=list)
    prompts: list[dict[str, Any]] = field(default_factory=list)
    retrievals: list[dict[str, Any]] = field(default_factory=list)
    guard_checks: list[dict[str, Any]] = field(default_factory=list)
    citation_support: list[dict[str, Any]] = field(default_factory=list)
    cap_reached: bool = False

    def start_case(self, case_id: str) -> None:
        self.case_id = case_id
        self.reservations = []
        self.prompts = []
        self.retrievals = []
        self.guard_checks = []
        self.citation_support = []

    def reserve(self, amount_microusd: int) -> None:
        try:
            self.ledger.reserve(
                amount_microusd, self.kind, f"{self.run_label} {self.case_id}".strip()
            )
        except SpendCapReached:
            self.cap_reached = True
            raise
        self.reservations.append({"kind": self.kind, "microusd": amount_microusd})


@contextmanager
def _patched(module: object, name: str, value: object) -> Iterator[None]:
    original = getattr(module, name)
    setattr(module, name, value)
    try:
        yield
    finally:
        setattr(module, name, original)


@contextmanager
def instrumented(recorder: CallRecorder, condition: Condition) -> Iterator[None]:
    """Route every budget reservation of `app.ai` through the ledger, label it as a search or
    a generation, and record what `CallRecorder` describes: the passages and scores of each
    search, the hashes of each generation's instructions and schema, the `model` field and
    the body of its response, which guard checks withheld an output, and which citations the
    discovery support check kept. Nothing the app returns or logs changes. Under "no-rag",
    the explanation adapter runs with `retrieval=False`. Every original is restored on exit.
    """
    reserve_budget = ai.reserve_budget
    vector_search = ai.openai_vector_search
    openai_json = ai.openai_json
    output_text = ai._output_text
    check_discovery = ai_guard.check_discovery
    check_explanation = ai_guard.check_explanation
    supported_suggestions = ai_guard.supported_suggestions

    def guarded_reserve(services: Services, amount_microusd: int) -> None:
        recorder.reserve(amount_microusd)
        reserve_budget(services, amount_microusd)

    async def labelled_search(
        query: str,
        vector_store_id: str,
        max_results: int,
        filters: Mapping[str, object] | None,
        services: Services,
    ) -> list[RetrievedPassage]:
        recorder.kind = "search"
        try:
            passages = await vector_search(query, vector_store_id, max_results, filters, services)
        finally:
            recorder.kind = "generation"
        recorder.retrievals.append(
            {"query": query, "passages": [_passage_record(item) for item in passages]}
        )
        return passages

    def recorded_check(name: str, check: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> list[ai_guard.GuardProblem]:
            problems: list[ai_guard.GuardProblem] = check(*args, **kwargs)
            recorder.guard_checks.append(
                {
                    "check": name,
                    "problems": [
                        {"reason": problem.reason, "where": problem.where} for problem in problems
                    ],
                }
            )
            return problems

        return wrapper

    def recorded_support(
        suggestions: Sequence[ai_guard.ProviderSuggestion], *args: Any
    ) -> list[ai_guard.ProviderSuggestion]:
        kept: list[ai_guard.ProviderSuggestion] = supported_suggestions(suggestions, *args)
        recorder.citation_support.append(
            {
                "cited": [_suggestion_record(item) for item in suggestions],
                "kept": [_suggestion_record(item) for item in kept],
            }
        )
        return kept

    async def recorded_json(
        instructions: str,
        user_input: str,
        schema: Mapping[str, object],
        schema_name: str,
        max_output_tokens: int,
        services: Services,
    ) -> str:
        recorder.prompts.append(
            {
                "schema_name": schema_name,
                "instructions_sha256": _sha256(instructions),
                "schema_sha256": _sha256(_canonical(schema)),
            }
        )
        return await openai_json(
            instructions, user_input, schema, schema_name, max_output_tokens, services
        )

    def served_model_text(body: Mapping[str, object]) -> str:
        # Read before the output is parsed, so an incomplete answer still names its model and
        # keeps its raw output.
        if recorder.prompts:
            served = body.get("model")
            recorder.prompts[-1]["served_model"] = served if isinstance(served, str) else None
            recorder.prompts[-1]["provider_response"] = provider_response_record(body)
        return output_text(body)

    with ExitStack() as stack:
        stack.enter_context(_patched(ai, "reserve_budget", guarded_reserve))
        stack.enter_context(_patched(ai, "openai_vector_search", labelled_search))
        stack.enter_context(_patched(ai, "openai_json", recorded_json))
        stack.enter_context(_patched(ai, "_output_text", served_model_text))
        stack.enter_context(
            _patched(ai_guard, "check_discovery", recorded_check("discovery", check_discovery))
        )
        stack.enter_context(
            _patched(
                ai_guard, "check_explanation", recorded_check("explanation", check_explanation)
            )
        )
        stack.enter_context(_patched(ai_guard, "supported_suggestions", recorded_support))
        if condition == "no-rag":
            no_retrieval = partial(explain_adapter.explain, retrieval=False)
            stack.enter_context(_patched(explain_adapter, "explain", no_retrieval))
        yield


def _passage_record(passage: RetrievedPassage) -> dict[str, Any]:
    return {
        "source_id": passage.source_id,
        "section_id": passage.section_id,
        "file_id": passage.file_id,
        "score": passage.score,
        "text": passage.text,
        "content_sha256": passage.content_sha256,
    }


def _suggestion_record(suggestion: ai_guard.ProviderSuggestion) -> dict[str, Any]:
    return {"variable_id": suggestion.variable_id, "source_ids": list(suggestion.source_ids)}


# The suite


def suite_kind(suite: Mapping[str, Any]) -> SuiteKind:
    """The kind of a suite: "planner" for planner/discovery, "rag" for rag_suite and rag_dev."""
    name = suite.get("suite")
    if name == "planner":
        return "planner"
    if isinstance(name, str) and name.startswith("rag"):
        return "rag"
    raise SuiteError('A suite\'s "suite" is "planner" or starts with "rag".')


def load_suite(path: Path) -> dict[str, Any]:
    """The suite at `path`, checked before anything is sent. Raises `SuiteError`."""
    try:
        suite = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SuiteError(f"The suite {path} cannot be read.") from error
    if not isinstance(suite, dict):
        raise SuiteError("A suite is a JSON object.")
    kind = suite_kind(suite)
    if kind == "rag" and "must_not_vocabulary" not in suite:
        # rag_dev.json's scoring notes say it shares the held-out suite's vocabulary.
        suite["must_not_vocabulary"] = _shared_vocabulary(path.with_name(RAG_SUITE_FILE))
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SuiteError("A suite has a non-empty list of cases.")
    seen: set[str] = set()
    for case in cases:
        problem = _planner_problem(case, suite) if kind == "planner" else _rag_problem(case, suite)
        if problem is None and case["id"] in seen:
            problem = "a repeated id"
        if problem is not None:
            name = case.get("id") if isinstance(case, dict) else case
            raise SuiteError(f"Case {name!r} has {problem}.")
        seen.add(case["id"])
    return suite


def _shared_vocabulary(path: Path) -> dict[str, str]:
    try:
        vocabulary = json.loads(path.read_text(encoding="utf-8"))["must_not_vocabulary"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise SuiteError(f"The must_not vocabulary of {path} cannot be read.") from error
    if not isinstance(vocabulary, dict):
        raise SuiteError(f"The must_not vocabulary of {path} is not an object.")
    return vocabulary


def _common_problem(case: object, required: frozenset[str]) -> str | None:
    if not isinstance(case, dict):
        return "no object"
    if not isinstance(case.get("id"), str) or not isinstance(case.get("category"), str):
        return "no string id or category"
    if not isinstance(case.get("question"), str) and not isinstance(case.get("raw_body"), str):
        return "neither a question nor a raw_body"
    expected = case.get("expected")
    if not isinstance(expected, dict):
        return "no expected object"
    absent = required - set(expected)
    return f"no expected {sorted(absent)}" if absent else None


def _planner_problem(case: object, suite: Mapping[str, Any]) -> str | None:
    problem = _common_problem(case, PLANNER_EXPECTED_KEYS)
    if problem is not None or not isinstance(case, dict):
        return problem
    if case.get("endpoint") not in ("discover", "plan"):
        return 'an endpoint other than "discover" or "plan"'
    unknown = set(case["expected"]["notices"]) - set(NOTICE_PREFIXES)
    if unknown:
        return f"unknown notice keys {sorted(unknown)}"
    support = case["expected"].get("citation_support", "not_applicable")
    if support not in CITATION_SUPPORT_VALUES:
        return f"an unknown citation_support {support!r}"
    if support == "every_suggestion" and not isinstance(
        suite.get("citation_sections_by_variable"), dict
    ):
        return "citation_support but no citation_sections_by_variable in the suite"
    return None


def _rag_problem(case: object, suite: Mapping[str, Any]) -> str | None:
    problem = _common_problem(case, RAG_EXPECTED_KEYS)
    if problem is not None or not isinstance(case, dict):
        return problem
    investigation = case.get("investigation")
    if investigation is None:
        if not isinstance(case.get("investigation_id"), str):
            return "neither an investigation nor an investigation_id"
    elif investigation not in suite.get("investigations", {}):
        return f"an unknown investigation {investigation!r}"
    unknown = set(case["expected"]["must_not"]) - set(suite.get("must_not_vocabulary", {}))
    if unknown:
        return f"must_not items outside the vocabulary {sorted(unknown)}"
    retrieval = case["expected"].get("expected_retrieval_any", [])
    if not isinstance(retrieval, list) or not all(isinstance(item, str) for item in retrieval):
        return "an expected_retrieval_any that is not a list of section IDs"
    return None


def case_endpoint(case: Mapping[str, Any], kind: SuiteKind) -> str:
    return "explain" if kind == "rag" else str(case["endpoint"])


def case_payload(case: Mapping[str, Any], kind: SuiteKind, investigation_id: str | None) -> str:
    """The request body of a case: its raw body as given, else the JSON request."""
    if isinstance(case.get("raw_body"), str):
        return str(case["raw_body"])
    payload: dict[str, object] = {"question": case["question"]}
    if kind == "rag":
        payload["investigation_id"] = investigation_id
    elif "draft" in case:
        payload["draft"] = case["draft"]
    return json.dumps(payload, ensure_ascii=False)


def case_investigation_id(
    case: Mapping[str, Any], suite: Mapping[str, Any], recorded: Mapping[str, Any]
) -> str | None:
    """The ID a RAG case sends: its literal one, else the recorded ID of its example."""
    if case.get("investigation") is None:
        return case.get("investigation_id")
    query = suite["investigations"][case["investigation"]]["query"]
    record = recorded.get(query) or {}
    return record.get("investigation_id")


# Reading a response


def _proposal(endpoint: str, http_status: int | None, body: object) -> dict[str, Any] | None:
    """The response's proposal: the body of a successful /api/plan, else its `proposal`."""
    if http_status != 200 or not isinstance(body, dict):
        return None
    if endpoint == "plan":
        return body
    proposal = body.get("proposal")
    return proposal if isinstance(proposal, dict) else None


def _has_notice(proposal: Mapping[str, Any] | None, key: str) -> bool:
    if proposal is None:
        return False
    return any(notice.startswith(NOTICE_PREFIXES[key]) for notice in proposal.get("notices", []))


def planner_outcome(endpoint: str, http_status: int | None, body: object) -> str:
    """What a planner case resolved to (backend/evaluation/README.md, `statuses`)."""
    if http_status == 400:
        return "bad_request"
    if http_status != 200 or not isinstance(body, dict):
        return f"error:{_error_code(body) or http_status}"
    if endpoint == "plan":
        return "clarify" if _has_notice(body, "needs_clarification") else "proposal"
    return str(body.get("status"))


def _error_code(body: object) -> str | None:
    error = body.get("error") if isinstance(body, dict) else None
    return error.get("code") if isinstance(error, dict) else None


def generated_texts(body: object) -> list[str]:
    """Every text the model wrote that a discovery or explanation response shows."""
    if not isinstance(body, dict):
        return []
    clarification = body.get("clarification") or {}
    return [
        *(item["reason"] for item in body.get("suggestions") or []),
        *(block["text"] for block in body.get("blocks") or []),
        *([clarification["question"]] if "question" in clarification else []),
        *(choice["label"] for choice in clarification.get("choices", [])),
    ]


def response_citations(body: object) -> list[dict[str, Any]]:
    if not isinstance(body, dict):
        return []
    items = [*(body.get("suggestions") or []), *(body.get("blocks") or [])]
    return [citation for item in items for citation in item["citations"]]


def has_unlisted_number(text: str) -> bool:
    """Whether `text` writes a number: a token with a digit that is not a year, a range of
    years or a letter-first identifier. Years outside the period are not told apart here.
    """
    return any(
        any(character.isdigit() for character in token)
        and not _YEARS.fullmatch(token)
        and not _IDENTIFIER.fullmatch(token)
        for token in _TOKEN.findall(text)
    )


def _check(name: str, passed: bool, detail: object = None) -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "detail": detail}


# Planner and discovery checks (backend/evaluation/README.md)


def check_planner_case(
    expected: Mapping[str, Any],
    endpoint: str,
    http_status: int | None,
    body: object,
    cutoff: int,
    citation_sections: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """The automated checks, critical errors and reviewer items of one planner case.
    `citation_sections` is the suite's `citation_sections_by_variable` (empty when it has none).
    """
    outcome = planner_outcome(endpoint, http_status, body)
    proposal = _proposal(endpoint, http_status, body)
    data = body if isinstance(body, dict) else {}
    checks = [_check("status", outcome in expected["statuses"], outcome)]
    if outcome == "unsupported":
        reason = data.get("reason")
        checks.append(_check("reason", reason in expected["reasons"], reason))
    # README: field checks apply only when the response holds a proposal.
    if proposal is not None:
        checks += _field_checks(expected, endpoint, data, proposal, cutoff)
    if expected["must_clarify"]:
        checks.append(
            _check("must_clarify", _asks(endpoint, outcome, data, proposal, expected), outcome)
        )
    if expected["must_refuse"]:
        checks.append(_check("must_refuse", _refuses(endpoint, outcome, data, proposal), outcome))
    support = _citation_support_check(expected, data, citation_sections)
    if support is not None:
        checks.append(support)
    texts = generated_texts(body)
    critical = _planner_critical(expected, data, proposal, cutoff)
    # Round-2 README: a suggestion citing no section about its own variable is a fabricated
    # citation, a critical error.
    if support is not None and not support["passed"]:
        critical.append("fabricated_citation")
    # README "Critical errors": generated text that writes a number is critical.
    if any(has_unlisted_number(text) for text in texts):
        critical.append("write_number")
    review = []
    if texts:
        review.append("generated_text_claims")
        if expected["premise_must_not_be_endorsed"]:
            review.append("premise_must_not_be_endorsed")
    return {"outcome": outcome, "checks": checks, "critical": critical, "review_pending": review}


def _citation_support_check(
    expected: Mapping[str, Any],
    data: Mapping[str, Any],
    citation_sections: Mapping[str, Sequence[str]],
) -> dict[str, Any] | None:
    """Round-2 `citation_support`: with "every_suggestion", every suggestion in the response,
    whatever its status, cites at least one section listed for its own variable. The detail
    names the variables whose suggestions do not. None when the case does not ask for it.
    """
    if expected.get("citation_support") != "every_suggestion":
        return None
    unsupported = [
        item["variable"]["id"]
        for item in data.get("suggestions") or []
        if not {citation["section_id"] for citation in item["citations"]}
        & set(citation_sections.get(item["variable"]["id"], ()))
    ]
    return _check("citation_support", not unsupported, unsupported)


def _field_checks(
    expected: Mapping[str, Any],
    endpoint: str,
    data: Mapping[str, Any],
    proposal: Mapping[str, Any],
    cutoff: int,
) -> list[dict[str, Any]]:
    checks = []
    variable = _first_variable(endpoint, data, proposal)
    if expected["variables"]["mode"] == "in":
        checks.append(_check("variables", variable in expected["variables"]["ids"], variable))
    places = expected["places"]
    names = [place["name"] for place in proposal.get("places", [])]
    if places["check"]:
        asks_place = _asks_for(endpoint, data, proposal, ("place",))
        checks.append(_check("places", _places_fit(places, names, asks_place), names))
    starts = {entry.id: entry.record_start for entry in load_catalogue()}
    record_start = starts.get(variable) if variable else None
    for key in ("from", "to"):
        if expected[key] != "any":
            allowed = _years(expected[key], record_start, cutoff)
            checks.append(_check(key, proposal.get(key) in allowed, proposal.get(key)))
    if expected["season"] != "any":
        season = proposal.get("season")
        checks.append(_check("season", season == expected["season"], season))
    absent = [key for key in expected["notices"] if not _has_notice(proposal, key)]
    checks.append(_check("notices", not absent, absent))
    if endpoint == "discover" and expected["missing_includes"]:
        missing = data.get("missing") or []
        found = all(name in missing for name in expected["missing_includes"])
        checks.append(_check("missing_includes", found, missing))
    return checks


def _first_variable(
    endpoint: str, data: Mapping[str, Any], proposal: Mapping[str, Any]
) -> str | None:
    """The proposal's variable; for discovery, the first suggestion's (README, `variables`)."""
    if endpoint == "discover":
        suggestions = data.get("suggestions") or []
        return suggestions[0]["variable"]["id"] if suggestions else None
    variables = proposal.get("variables") or []
    return variables[0]["id"] if variables else None


def _years(value: object, record_start: int | None, cutoff: int) -> list[int | None]:
    """The years an expected `from` or `to` accepts: a year, a token or a list of them."""
    values = value if isinstance(value, list) else [value]
    tokens = {"record_start": record_start, "cutoff": cutoff}
    return [tokens[item] if isinstance(item, str) else item for item in values]


def _places_fit(places: Mapping[str, Any], names: Sequence[str], asks_place: bool) -> bool:
    resolved = set(names)
    if any(resolved == set(accepted) for accepted in places["accept"]):
        return True
    if places["ask_ok"] and not resolved and asks_place:
        return True
    subset = set(places["subset_of"])
    return bool(subset) and 1 <= len(resolved) <= 2 and resolved <= subset


def _asks_for(
    endpoint: str,
    data: Mapping[str, Any],
    proposal: Mapping[str, Any] | None,
    fields: Sequence[str],
) -> bool:
    """Whether the response leaves a setting for the user and says so: a clarification, a
    choose-place or needs-clarification notice, or a discover "ready" whose `missing` names
    one of `fields`.
    """
    if endpoint == "discover" and data.get("status") == "clarify":
        return True
    if _has_notice(proposal, "choose_place") or _has_notice(proposal, "needs_clarification"):
        return True
    missing = data.get("missing") or []
    ready = endpoint == "discover" and data.get("status") == "ready"
    return ready and any(name in missing for name in fields)


def _asks(
    endpoint: str,
    outcome: str,
    data: Mapping[str, Any],
    proposal: Mapping[str, Any] | None,
    expected: Mapping[str, Any],
) -> bool:
    """README `must_clarify`. The "open field" of a discover "ready" is every field of
    `missing_includes` when the case names some, else a setting with no default.
    """
    if outcome == "clarify":
        return True
    named = expected["missing_includes"]
    if named and endpoint == "discover" and data.get("status") == "ready":
        return all(name in (data.get("missing") or []) for name in named)
    return _asks_for(endpoint, data, proposal, CHOOSABLE_FIELDS)


def _refuses(
    endpoint: str, outcome: str, data: Mapping[str, Any], proposal: Mapping[str, Any] | None
) -> bool:
    if endpoint == "discover":
        return outcome == "unsupported" and not data.get("suggestions")
    return _has_notice(proposal, "needs_clarification")


def _planner_critical(
    expected: Mapping[str, Any],
    data: Mapping[str, Any],
    proposal: Mapping[str, Any] | None,
    cutoff: int,
) -> list[str]:
    """README "Critical errors" that need no reading: a forbidden string anywhere in the
    response, a place resolved where the case must ask, and a year after the cutoff proposed
    without the unsupported-dates notice.
    """
    critical = []
    text = json.dumps(data, ensure_ascii=False).casefold()
    if any(phrase.casefold() in text for phrase in expected["must_not_contain"]):
        critical.append("must_not_contain")
    places = expected["places"]
    must_ask = places["check"] and not places["accept"] and places["ask_ok"]
    if must_ask and not places["subset_of"] and proposal and proposal.get("places"):
        critical.append("place_resolved_where_asking")
    years = [proposal.get(key) for key in ("from", "to")] if proposal else []
    late = any(isinstance(year, int) and year > cutoff for year in years)
    if late and not _has_notice(proposal, "unsupported_dates"):
        critical.append("future_year_without_notice")
    return critical


# RAG checks (the scoring notes of backend/evaluation/rag_suite.json)


def check_rag_case(
    expected: Mapping[str, Any],
    http_status: int | None,
    body: object,
    requested_id: str | None,
    reservations: Sequence[Mapping[str, Any]],
    manifest_sections: frozenset[str],
    vocabulary: Mapping[str, str],
) -> dict[str, Any]:
    """The automated checks, critical errors and reviewer items of one RAG case."""
    data = body if isinstance(body, dict) else {}
    must_not = list(expected["must_not"])
    if "error" in expected:
        error = expected["error"]
        code = _error_code(body)
        failed_as_expected = http_status == error["http_status"] and code == error["code"]
        checks = [_check("error", failed_as_expected, [http_status, code])]
        if "model_call" in must_not:
            checks.append(_check("model_call", not reservations, len(reservations)))
        return _rag_result(http_status, data, checks, [], vocabulary)
    status = data.get("status") if http_status == 200 else f"error:{_error_code(body)}"
    checks = [_check("status", status in expected["statuses"], status)]
    blocks = data.get("blocks") or []
    if status == "answered":
        checks += _answer_checks(expected, blocks)
    if status == "new_investigation_required" and "proposal" in expected:
        checks.append(_proposal_check(expected["proposal"], data.get("proposal")))
    if http_status == 200:
        bound = data.get("investigation_id") == requested_id
        checks.append(_check("bound_to_investigation", bound, data.get("investigation_id")))
    cited = [item["section_id"] for item in response_citations(body)]
    unknown = [section for section in cited if section not in manifest_sections]
    checks.append(_check("fabricated_citation", not unknown, unknown))
    texts = generated_texts(body)
    checks += _text_checks(must_not, texts)
    automated = {"write_number", "include_url", "reveal_secret", "model_call"}
    review = [item for item in must_not if item not in automated] if texts else []
    if texts:
        review += ["fabricated_citation", "unsupported_claim"]
    return _rag_result(http_status, data, checks, list(dict.fromkeys(review)), vocabulary)


def _answer_checks(
    expected: Mapping[str, Any], blocks: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    cited = {citation["section_id"] for block in blocks for citation in block["citations"]}
    sections = expected["sections_any"]
    checks = []
    if sections == "none":
        checks.append(_check("sections_any", False, sorted(cited)))
    elif sections:
        checks.append(_check("sections_any", bool(cited & set(sections)), sorted(cited)))
    if "references_any" in expected:
        fields = {reference["field"] for block in blocks for reference in block["references"]}
        hit = bool(fields & set(expected["references_any"]))
        checks.append(_check("references_any", hit, sorted(fields)))
    return checks


def _proposal_check(
    expected: Mapping[str, Any], proposal: Mapping[str, Any] | None
) -> dict[str, Any]:
    """The scoring note on `expected.proposal`: variable, places, years and season."""
    if proposal is None:
        return _check("proposal", False, None)
    variables = [variable["id"] for variable in proposal.get("variables", [])]
    places = proposal.get("places", [])
    problems = []
    if "variable_any" in expected and (variables[:1] or [None])[0] not in expected["variable_any"]:
        problems.append("variable")
    include = expected.get("places_include", [])
    if not all(any(_names_place(name, place) for place in places) for name in include):
        problems.append("places_include")
    if "places_exactly" in expected and not _same_places(expected["places_exactly"], places):
        problems.append("places_exactly")
    for key in ("from", "to"):
        if key in expected and proposal.get(key) != expected[key]:
            problems.append(key)
    if "season_any" in expected and proposal.get("season") not in expected["season_any"]:
        problems.append("season")
    detail = {"problems": problems, "variables": variables, "places": [p["name"] for p in places]}
    return _check("proposal", not problems, detail)


def _names_place(name: str, place: Mapping[str, Any]) -> bool:
    """A name matches a proposed place by its label, ignoring case, or by the reviewed place
    the name resolves to, so "Svalbard" matches the place labelled "Longyearbyen".
    """
    if name.casefold() == str(place["name"]).casefold():
        return True
    reviewed = resolve_place_query(name)
    return reviewed is not None and (reviewed.lat, reviewed.lon) == (place["lat"], place["lon"])


def _same_places(names: Sequence[str], places: Sequence[Mapping[str, Any]]) -> bool:
    return (
        len(names) == len(places)
        and all(any(_names_place(name, place) for place in places) for name in names)
        and all(any(_names_place(name, place) for name in names) for place in places)
    )


def _text_checks(must_not: Sequence[str], texts: Sequence[str]) -> list[dict[str, Any]]:
    """The `must_not` items a pattern can decide: a number, a URL or a key-like string."""
    detectors = {
        "write_number": has_unlisted_number,
        "include_url": lambda text: _URL.search(text) is not None,
        "reveal_secret": lambda text: _SECRET.search(text) is not None,
    }
    checks = []
    for item in must_not:
        detector = detectors.get(item)
        if detector is not None:
            hits = [text for text in texts if detector(text)]
            checks.append(_check(item, not hits, hits))
    return checks


def _rag_result(
    http_status: int | None,
    data: Mapping[str, Any],
    checks: list[dict[str, Any]],
    review: list[str],
    vocabulary: Mapping[str, str],
) -> dict[str, Any]:
    critical = [
        check["check"]
        for check in checks
        if not check["passed"]
        and (
            check["check"] in ALWAYS_CRITICAL
            or vocabulary.get(check["check"], "").endswith(CRITICAL_MARK)
        )
    ]
    outcome = data.get("status") if http_status == 200 else f"error:{_error_code(data)}"
    return {"outcome": outcome, "checks": checks, "critical": critical, "review_pending": review}


def retrieval_relevance(
    expected: Mapping[str, Any], retrievals: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    """Round-2 retrieval relevance, scored apart from the pass result: relevant when any
    search of the case returned a section in `expected_retrieval_any`. None when the case
    lists no section (nothing in the corpus is on topic) or predates the key.
    """
    wanted = expected.get("expected_retrieval_any") or []
    if not wanted:
        return None
    returned = [
        passage["section_id"] for retrieval in retrievals for passage in retrieval["passages"]
    ]
    hits = sorted(set(returned) & set(wanted))
    return {"relevant": bool(hits), "hits": hits, "returned": returned}


def timed_out(http_status: int | None, body: object) -> bool:
    """Whether the request hit a deadline: the runner's own, or the endpoint's 30-second one,
    which answers 503 with a message saying the deadline expired.
    """
    if http_status is None:
        return True
    error = body.get("error") if isinstance(body, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    return http_status == 503 and "deadline expired" in (message or "")


def summarize(endpoint: str, http_status: int | None, body: object) -> dict[str, Any]:
    """The parts of a response the reviewer needs, without the full cited passages."""
    if not isinstance(body, dict):
        return {"error": {"code": "unreadable_body", "message": None}}
    if http_status != 200:
        return {"error": body.get("error")}
    if endpoint == "plan":
        return {"proposal": _proposal_summary(body)}
    summary = {key: body.get(key) for key in ("status", "reason", "missing", "notices")}
    summary["proposal"] = _proposal_summary(body.get("proposal"))
    if "suggestions" in body:
        summary["suggestions"] = [
            {
                "variable": item["variable"]["id"],
                "reason": item["reason"],
                "citations": [_citation_summary(citation) for citation in item["citations"]],
            }
            for item in body["suggestions"]
        ]
        summary["clarification"] = body.get("clarification")
    if "blocks" in body:
        summary["investigation_id"] = body.get("investigation_id")
        summary["blocks"] = [
            {
                "text": block["text"],
                "citations": [_citation_summary(citation) for citation in block["citations"]],
                "references": block["references"],
            }
            for block in body["blocks"]
        ]
    return summary


def _proposal_summary(proposal: object) -> dict[str, Any] | None:
    if not isinstance(proposal, dict):
        return None
    return {
        "variables": [variable["id"] for variable in proposal["variables"]],
        "places": [
            {key: place.get(key) for key in ("name", "lat", "lon", "kind")}
            for place in proposal["places"]
        ],
        "from": proposal.get("from"),
        "to": proposal.get("to"),
        "season": proposal.get("season"),
        "notices": proposal.get("notices"),
    }


def _citation_summary(citation: Mapping[str, Any]) -> dict[str, Any]:
    return {key: citation.get(key) for key in ("source_id", "section_id", "kind")}


# The report


def wilson_interval(passed: int, total: int, z: float = WILSON_Z_95) -> tuple[float, float] | None:
    """The Wilson score interval of a pass rate, as (low, high) proportions; None for no cases."""
    if total == 0:
        return None
    rate = passed / total
    denominator = 1 + z**2 / total
    centre = (rate + z**2 / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z**2 / (4 * total**2)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def percentile(values: Sequence[float], fraction: float) -> float | None:
    """The nearest-rank percentile of `values`; None when there are none."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def report(results: Mapping[str, Any]) -> dict[str, Any]:
    """Counts by category, the automated pass rate with its Wilson 95% interval, critical
    errors, the failures, cases awaiting review, retrieval relevance where a case scores it,
    latency (median, 90th percentile, maximum, in seconds), timeouts, the total reserved cost
    and the identities sent. Cases not run (the spend cap) are counted apart, outside the pass
    rate; their reservations count in the cost.
    """
    cases = results["cases"]
    run = [case for case in cases if "not_run" not in case]
    passed = sum(1 for case in run if case["passed"])
    categories: dict[str, dict[str, int]] = {}
    for case in cases:
        counts = categories.setdefault(
            case["category"], {"cases": 0, "passed": 0, "failed": 0, "not_run": 0}
        )
        counts["cases"] += 1
        if "not_run" in case:
            counts["not_run"] += 1
        else:
            counts["passed" if case["passed"] else "failed"] += 1
    latencies = [case["latency_seconds"] for case in run if case["latency_seconds"] is not None]
    interval = wilson_interval(passed, len(run))
    # A case the spend cap interrupted keeps the reservations it made.
    reserved = sum(item["microusd"] for case in cases for item in case.get("reservations", []))
    relevance = [case["retrieval_relevance"] for case in run if case.get("retrieval_relevance")]
    return {
        "condition": results.get("condition"),
        "cases": len(cases),
        "run": len(run),
        "not_run": len(cases) - len(run),
        "passed": passed,
        "failed": len(run) - passed,
        "pass_rate": passed / len(run) if run else None,
        "wilson95": list(interval) if interval else None,
        "target_pass_rate": results.get("target_pass_rate"),
        "by_category": categories,
        "critical": {case["id"]: case["critical"] for case in run if case["critical"]},
        "failures": [
            {
                "id": case["id"],
                "category": case["category"],
                "outcome": case["outcome"],
                "failed_checks": [
                    check["check"] for check in case["checks"] if not check["passed"]
                ],
            }
            for case in run
            if not case["passed"]
        ],
        "review_pending": sum(1 for case in run if case["review_pending"]),
        "retrieval_relevance": {
            "scored": len(relevance),
            "relevant": sum(1 for item in relevance if item["relevant"]),
            "not_relevant": [
                case["id"]
                for case in run
                if case.get("retrieval_relevance") and not case["retrieval_relevance"]["relevant"]
            ],
        },
        "latency_seconds": {
            "median": statistics.median(latencies) if latencies else None,
            "p90": percentile(latencies, LATENCY_PERCENTILE),
            "max": max(latencies) if latencies else None,
        },
        "timeouts": sum(1 for case in run if case["timed_out"]),
        "searches": sum(_count(case, "search") for case in cases),
        "generations": sum(_count(case, "generation") for case in cases),
        "reserved_microusd": reserved,
        "reserved_usd": reserved / MICROUSD_PER_USD,
        "sent": sent_identities(results),
    }


def _count(case: Mapping[str, Any], kind: CallKind) -> int:
    return sum(1 for item in case.get("reservations", []) if item["kind"] == kind)


def sent_identities(results: Mapping[str, Any]) -> dict[str, Any]:
    """What the run's generations actually sent and were served, from the per-case records:
    the distinct (schema name, instructions hash, schema hash) triples with their call counts,
    and the distinct model names the provider reported. A results file written before the
    served model was recorded has none.
    """
    calls: dict[tuple[str, str, str], int] = {}
    served: set[str] = set()
    for case in results["cases"]:
        for prompt in case.get("prompts", []):
            key = (prompt["schema_name"], prompt["instructions_sha256"], prompt["schema_sha256"])
            calls[key] = calls.get(key, 0) + 1
            if prompt.get("served_model"):
                served.add(prompt["served_model"])
    prompts = [
        {"schema_name": name, "instructions_sha256": sent, "schema_sha256": schema, "calls": count}
        for (name, sent, schema), count in sorted(calls.items())
    ]
    return {"prompts": prompts, "served_models": sorted(served)}


def _sent_prompts(results: Mapping[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (item["schema_name"], item["instructions_sha256"], item["schema_sha256"])
        for item in sent_identities(results)["prompts"]
    }


def paired_comparison(rag: Mapping[str, Any], no_rag: Mapping[str, Any]) -> dict[str, Any]:
    """The same cases under both conditions: improvements (pass only with retrieval),
    regressions (pass only without), both passing and both failing, and whether the frozen
    identities other than the condition match: the configuration frozen before the run, and
    the instructions and schemas actually sent.
    """
    with_rag = {case["id"]: case["passed"] for case in rag["cases"] if "not_run" not in case}
    without = {case["id"]: case["passed"] for case in no_rag["cases"] if "not_run" not in case}
    shared = [case_id for case_id in with_rag if case_id in without]
    identity_keys = ("model", "schema_sha256", "corpus_version", "suite_sha256")
    mismatched = [
        key for key in identity_keys if rag["identities"].get(key) != no_rag["identities"].get(key)
    ]
    if _sent_prompts(rag) != _sent_prompts(no_rag):
        mismatched.append("sent_prompts")
    return {
        "paired_cases": len(shared),
        "both_passed": [i for i in shared if with_rag[i] and without[i]],
        "improvements": [i for i in shared if with_rag[i] and not without[i]],
        "regressions": [i for i in shared if not with_rag[i] and without[i]],
        "both_failed": [i for i in shared if not with_rag[i] and not without[i]],
        "identities_matched": not mismatched,
        "mismatched_identities": mismatched,
    }


# Running a suite


def evaluation_settings(base: Settings, state_dir: Path) -> Settings:
    """`base` with this process's evaluation overrides; see the module docstring."""
    return replace(
        base,
        discovery_evaluated=True,
        rag_evaluated=True,
        ai_rate_per_minute=EVALUATION_RATE_PER_MINUTE,
        rate_limit_per_minute=EVALUATION_RATE_PER_MINUTE,
        cache_path=state_dir / "power.sqlite",
        operational_path=state_dir / "operations.sqlite",
        snapshot_path=state_dir / "snapshots",
    )


def evaluation_ledger(settings: Settings) -> SpendLedger:
    """Load the cumulative ledger without exceeding the configured daily allowance.

    The ledger is deliberately stricter than a daily counter: it does not reset when
    another suite, process, scratch state directory or calendar day starts.
    """
    if settings.ai_daily_budget_microusd <= 0:
        raise SuiteError("Set a positive AI_DAILY_BUDGET_MICROUSD before paid evaluation.")
    return SpendLedger.load(
        LEDGER_PATH, cap_microusd=min(SPEND_CAP_MICROUSD, settings.ai_daily_budget_microusd)
    )


def prepare_state(state_dir: Path) -> None:
    """Create the scratch state; its cache starts as a copy of the repository's state cache,
    else of the shipped seed, and is kept across runs so matched conditions share evidence.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    cache = state_dir / "power.sqlite"
    if not cache.exists():
        shutil.copyfile(STATE_CACHE if STATE_CACHE.exists() else SEED_CACHE, cache)


def identities(settings: Settings, corpus: Corpus, suite_path: Path, cutoff: int) -> dict[str, Any]:
    """What the results depend on, frozen before the first call. `model` is the name the
    settings request, which may be an alias; the instructions actually sent and the model the
    provider served are recorded per generation (`sent_identities`).
    """
    diff = _git("diff", "HEAD", "--binary")
    return {
        "model": settings.ai_model,
        "provider": settings.ai_provider,
        "schema_sha256": {
            "discover": _sha256(_canonical(discover_adapter.SCHEMA)),
            "explain": _sha256(_canonical(explain_adapter.SCHEMA)),
            "plan": _sha256(_canonical(ExtractedPlan.model_json_schema())),
        },
        "corpus_version": corpus.version,
        "vector_store_id": settings.rag_vector_store_id,
        "git_head": _git("rev-parse", "HEAD").decode().strip(),
        # Untracked files are not part of this hash.
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "tracked_diff_empty": diff == b"",
        "suite_sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        "last_complete_year": cutoff,
        "started_utc": _now(),
        "bounds": {
            "max_passages": MAX_PASSAGES,
            "discover_max_output_tokens": discover_adapter.MAX_OUTPUT_TOKENS,
            "explain_max_output_tokens": explain_adapter.MAX_OUTPUT_TOKENS,
            "deadline_seconds": ai.DEADLINE_SECONDS,
            "reasoning_effort": ai.REASONING_EFFORT,
        },
        "prices_microusd": {
            "input_per_million_tokens": settings.ai_input_microusd_per_million,
            "output_per_million_tokens": settings.ai_output_microusd_per_million,
            "search_per_call": settings.rag_search_microusd_per_call,
        },
    }


async def record_cases(client: httpx.AsyncClient, suite: Mapping[str, Any]) -> dict[str, Any]:
    """Open every frozen example case, and every investigation the suite names, through
    /api/case, which records it for /api/explain. Maps each case query to its outcome.
    """
    queries = [example.query for example in load_examples()]
    queries += [entry["query"] for entry in suite.get("investigations", {}).values()]
    recorded: dict[str, Any] = {}
    for query in dict.fromkeys(queries):
        response = await client.get("/api/case?" + query)
        body = response.json()
        ok = response.status_code == 200
        recorded[query] = {
            "http": response.status_code,
            "investigation_id": body.get("id") if ok else None,
            "pinned": body.get("pinned") if ok else None,
            "verdict_kinds": [result["verdict"]["kind"] for result in body["results"]]
            if ok
            else None,
            "places": [
                {
                    "label": result["place"]["name"],
                    "kind": result["verdict"]["kind"],
                    "direction": result["verdict"]["direction"],
                }
                for result in body["results"]
            ]
            if ok
            else [],
            "variable": body["variable"]["id"] if ok else None,
            "data_sources": [
                {"name": source["name"], "product": source["product"]} for source in body["sources"]
            ]
            if ok
            else [],
        }
    return recorded


@dataclass(frozen=True)
class RunContext:
    """What every case of one run shares."""

    suite: Mapping[str, Any]
    kind: SuiteKind
    recorded: Mapping[str, Any]
    manifest_sections: frozenset[str]
    cutoff: int


async def run_case(
    client: httpx.AsyncClient,
    case: Mapping[str, Any],
    context: RunContext,
    recorder: CallRecorder,
) -> dict[str, Any]:
    """Send one case once and record what happened."""
    endpoint = case_endpoint(case, context.kind)
    investigation_id = (
        case_investigation_id(case, context.suite, context.recorded)
        if context.kind == "rag"
        else None
    )
    payload = case_payload(case, context.kind, investigation_id)
    recorder.start_case(case["id"])
    http_status: int | None = None
    body: object = None
    start = time.monotonic()
    try:
        async with asyncio.timeout(RUNNER_TIMEOUT_SECONDS):
            response = await client.post(
                ENDPOINT_PATHS[endpoint],
                content=payload.encode(),
                headers={"Content-Type": "application/json"},
            )
        http_status = response.status_code
        body = response.json()
    except TimeoutError:
        body = {"error": {"code": "runner_timeout", "message": "The runner's bound expired."}}
    except ValueError:
        body = None
    latency = time.monotonic() - start
    if context.kind == "rag":
        result = check_rag_case(
            case["expected"],
            http_status,
            body,
            investigation_id,
            recorder.reservations,
            context.manifest_sections,
            context.suite.get("must_not_vocabulary", {}),
        )
    else:
        result = check_planner_case(
            case["expected"],
            endpoint,
            http_status,
            body,
            context.cutoff,
            context.suite.get("citation_sections_by_variable", {}),
        )
    return {
        "id": case["id"],
        "category": case["category"],
        "endpoint": endpoint,
        "request": {"raw_body": payload} if "raw_body" in case else json.loads(payload),
        "http": http_status,
        "outcome": result["outcome"],
        "reason": body.get("reason") if isinstance(body, dict) else None,
        "response": summarize(endpoint, http_status, body),
        "latency_seconds": round(latency, 3),
        "timed_out": timed_out(http_status, body),
        "reservations": recorder.reservations,
        "reserved_microusd": sum(item["microusd"] for item in recorder.reservations),
        "prompts": recorder.prompts,
        "retrievals": recorder.retrievals,
        "guard_checks": recorder.guard_checks,
        "citation_support": recorder.citation_support,
        "retrieval_relevance": retrieval_relevance(case["expected"], recorder.retrievals),
        "checks": result["checks"],
        "passed": all(check["passed"] for check in result["checks"]),
        "critical": result["critical"],
        "review_pending": result["review_pending"],
        "number_flags": [text for text in generated_texts(body) if has_unlisted_number(text)],
    }


def suite_available(
    settings: Settings, kind: SuiteKind, cases: Sequence[Mapping[str, Any]]
) -> bool:
    """Whether the configured capabilities cover every endpoint the suite exercises."""
    if kind == "rag":
        return settings.explanation_available
    if any(case.get("endpoint") == "discover" for case in cases):
        return settings.discovery_available
    return settings.planner_available


async def run_suite(
    suite_path: Path,
    condition: Condition,
    limit: int | None,
    state_dir: Path,
    out_path: Path,
    ledger: SpendLedger,
) -> dict[str, Any]:
    """Run the suite and write the results after every case; returns the results."""
    suite = load_suite(suite_path)
    kind = suite_kind(suite)
    if kind == "planner" and condition == "no-rag":
        raise SuiteError("The no-rag condition applies to the RAG suites only.")
    prepare_state(state_dir)
    settings = evaluation_settings(load_settings(), state_dir)
    if not suite_available(settings, kind, suite["cases"]):
        raise SuiteError("The AI path of this suite is not configured in the environment.")
    corpus = load_corpus()
    services = build_services(settings)
    cutoff = services.tool_context().last_complete_year
    results: dict[str, Any] = {
        "suite": str(suite_path),
        "suite_kind": kind,
        "condition": condition,
        "target_pass_rate": suite.get("target_pass_rate", SPEC_TARGET_PASS_RATE),
        "assumed_cutoff": suite.get("assumed_cutoff"),
        "identities": identities(settings, corpus, suite_path, cutoff),
        "reviewer": None,
        "recorded_cases": {},
        "cases": [],
    }
    cases = suite["cases"][:limit] if limit is not None else suite["cases"]
    recorder = CallRecorder(ledger, run_label=f"{suite_path.name} {condition}")
    app = create_app(services, static_dir=state_dir / "no-web-app")
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=asgi_transport(app), base_url=BASE_URL) as client,
        ):
            with instrumented(recorder, condition):
                if kind == "rag":
                    results["recorded_cases"] = await record_cases(client, suite)
                context = RunContext(
                    suite, kind, results["recorded_cases"], frozenset(corpus.sections), cutoff
                )
                for case in cases:
                    outcome = await run_or_skip(client, case, context, recorder)
                    results["cases"].append(outcome)
                    _write_json(out_path, results)
                    if "not_run" not in outcome:
                        _progress(outcome, ledger)
    finally:
        await close_services(services)
    results["ledger_total_microusd"] = ledger.total_microusd
    results["report"] = report(results)
    _write_json(out_path, results)
    return results


def asgi_transport(app: FastAPI) -> httpx.ASGITransport:
    """The in-process transport to the app. A fault inside the app reaches the runner as that
    case's HTTP 500, like any other failure, instead of ending the run.
    """
    return httpx.ASGITransport(app=app, raise_app_exceptions=False)


async def run_or_skip(
    client: httpx.AsyncClient,
    case: Mapping[str, Any],
    context: RunContext,
    recorder: CallRecorder,
) -> dict[str, Any]:
    """`run_case`, unless the spend cap refuses a call: the case the refusal interrupts, and
    every case after it, is recorded as not run, outside the pass rate.
    """
    if recorder.cap_reached:
        return _not_run(case, [])
    outcome = await run_case(client, case, context, recorder)
    if recorder.cap_reached:
        return _not_run(case, outcome["reservations"])
    return outcome


def _not_run(case: Mapping[str, Any], reservations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "category": case["category"],
        "not_run": "spend_cap",
        "reservations": reservations,
    }


def _progress(outcome: Mapping[str, Any], ledger: SpendLedger) -> None:
    mark = "pass" if outcome["passed"] else "FAIL"
    print(
        f"{mark} {outcome['id']} http={outcome['http']} outcome={outcome['outcome']} "
        f"reason={outcome['reason']} {outcome['latency_seconds']}s "
        f"ledger={ledger.total_microusd / MICROUSD_PER_USD:.4f} USD",
        flush=True,
    )


# Helpers


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=REPO_DIR, capture_output=True, check=True, timeout=GIT_TIMEOUT_SECONDS
    ).stdout


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def provider_response_record(body: Mapping[str, object]) -> dict[str, object]:
    """The parts of a Responses body that a results file keeps (`PROVIDER_RESPONSE_KEYS`).
    A reasoning item of the output keeps everything but its `encrypted_content`, an opaque
    provider token that no reviewer can read.
    """
    record = {key: body[key] for key in PROVIDER_RESPONSE_KEYS if key in body}
    output = record.get("output")
    if isinstance(output, list):
        record["output"] = [_without_encrypted_content(item) for item in output]
    return record


def _without_encrypted_content(item: object) -> object:
    if isinstance(item, dict) and item.get("type") == "reasoning":
        return {key: value for key, value in item.items() if key != "encrypted_content"}
    return item


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_json(path: Path, value: object) -> None:
    """Write `value` to `path` through a temporary file, so a reader never sees half of it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a frozen evaluation suite (spec 12).")
    parser.add_argument("--suite", type=Path, help="the suite JSON file")
    parser.add_argument("--condition", choices=("rag", "no-rag"), default="rag")
    parser.add_argument("--out", type=Path, help="where to write the results JSON")
    parser.add_argument("--limit", type=int, help="run only the first N cases")
    parser.add_argument("--state-dir", type=Path, help="scratch directory for the app's state")
    parser.add_argument("--report", type=Path, help="print the report of a results file")
    parser.add_argument("--compare", type=Path, help="with --report: the no-rag results")
    args = parser.parse_args(argv)
    if args.report is not None:
        results = _read_json(args.report)
        printed: dict[str, Any] = {"report": report(results)}
        if args.compare is not None:
            printed["comparison"] = paired_comparison(results, _read_json(args.compare))
        print(json.dumps(printed, indent=1))
        return 0
    if args.suite is None or args.out is None or args.state_dir is None:
        parser.error("--suite, --out and --state-dir are required to run a suite")
    try:
        results = asyncio.run(
            run_suite(
                args.suite,
                args.condition,
                args.limit,
                args.state_dir,
                args.out,
                evaluation_ledger(load_settings()),
            )
        )
    except SuiteError as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps(results["report"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
