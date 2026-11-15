"""The shared AI bounds and OpenAI calls of spec 8, through fake transports only."""

import hashlib
import json
from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import httpx
import pytest
from fastapi import Request

from app import ai
from app.cache import Cache
from app.errors import AiUnavailableError, BadRequestError, RateLimitedError
from app.models import DocumentSource, RetrievedPassage
from app.ratelimit import RateLimiter
from app.services import Services
from tests.app_client import TODAY, make_services
from tests.fake_source import FakeSource

STORE_ID = "vs_test123"
SEARCH_PRICE = 2500
SCHEMA: dict[str, object] = {"type": "object", "properties": {}, "additionalProperties": False}
DAY = TODAY.isoformat()


@pytest.fixture
def services(tmp_path: Path) -> Iterator[Services]:
    cache = Cache(tmp_path / "cache.sqlite")
    operations = Cache(tmp_path / "operations.sqlite")
    service = make_services(cache, FakeSource())
    service.operations = operations
    service.settings = replace(
        service.settings,
        ai_provider="openai",
        ai_model="test-model",
        openai_api_key="test-key",
        ai_daily_turns=2,
        ai_daily_budget_microusd=1_000_000,
        ai_input_microusd_per_million=1_000_000,
        ai_output_microusd_per_million=1_000_000,
        rag_search_microusd_per_call=SEARCH_PRICE,
    )
    yield service
    cache.close()
    operations.close()


def fake_request(chunks: Sequence[bytes] = (), host: str = "203.0.113.5") -> Request:
    """Just what the shared helpers read from a request: its body stream and client host."""

    async def stream() -> AsyncIterator[bytes]:
        for chunk in chunks:
            yield chunk

    return cast(Request, SimpleNamespace(stream=stream, client=SimpleNamespace(host=host)))


def use_transport(
    monkeypatch: pytest.MonkeyPatch, answer: Callable[[httpx.Request], httpx.Response]
) -> list[httpx.Request]:
    """Route every client the module opens to `answer`, and collect the requests it saw."""
    requests: list[httpx.Request] = []
    original = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return answer(request)

    monkeypatch.setattr(
        ai.httpx,
        "AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler)),
    )
    return requests


def responses_body(*parts: dict[str, str], status: str = "completed") -> dict[str, object]:
    return {"status": status, "output": [{"type": "message", "content": list(parts)}]}


def search_hit(
    source_id: str | None,
    text: str,
    score: float = 0.8,
    section_id: str | None = "power-methodology-01",
) -> dict[str, object]:
    attributes: dict[str, str] = {"kind": "agency"}
    if source_id is not None:
        attributes["source_id"] = source_id
    if section_id is not None:
        attributes["section_id"] = section_id
    return {
        "file_id": "file-1",
        "filename": "section.txt",
        "score": score,
        "attributes": attributes,
        "content": [{"type": "text", "text": text}],
    }


def budget_used(services: Services) -> int:
    assert services.operations is not None
    return services.operations.get_counter("budget_microusd", DAY)


# Request bounds


@pytest.mark.anyio
async def test_body_within_the_bound_is_returned_whole() -> None:
    body = await ai.read_bounded_body(fake_request([b"a" * 4096, b"b" * 4096]), "too large")

    assert body == b"a" * 4096 + b"b" * 4096


@pytest.mark.anyio
async def test_body_over_eight_kib_is_a_bad_request() -> None:
    with pytest.raises(BadRequestError, match="too large"):
        await ai.read_bounded_body(fake_request([b"a" * 8192, b"b"]), "too large")


# The generation slot


@pytest.mark.anyio
async def test_generation_slot_refuses_a_second_generation_in_this_worker(
    services: Services,
) -> None:
    services.planner_busy = True

    with pytest.raises(RateLimitedError, match="already running"):
        async with ai.generation_slot(fake_request(), services):
            pass


@pytest.mark.anyio
async def test_generation_slot_refuses_while_another_worker_holds_the_lease(
    services: Services,
) -> None:
    assert services.operations is not None
    assert services.operations.acquire_lease(ai.GENERATION_LEASE, "other", 1e12, 60)

    with pytest.raises(RateLimitedError, match="Another"):
        async with ai.generation_slot(fake_request(), services):
            pass
    assert not services.planner_busy


@pytest.mark.anyio
async def test_generation_slot_releases_the_lease_and_flag_after_a_failure(
    services: Services,
) -> None:
    assert services.operations is not None

    with pytest.raises(ValueError, match="provider"):
        async with ai.generation_slot(fake_request(), services):
            assert services.planner_busy
            raise ValueError("provider failed")

    assert not services.planner_busy
    assert services.operations.acquire_lease(ai.GENERATION_LEASE, "after", 0.0, 30)


@pytest.mark.anyio
async def test_generation_slot_stops_at_the_daily_turn_limit(services: Services) -> None:
    for _ in range(services.settings.ai_daily_turns):
        async with ai.generation_slot(fake_request(), services):
            pass

    with pytest.raises(RateLimitedError, match="daily"):
        async with ai.generation_slot(fake_request(), services):
            pass


@pytest.mark.anyio
async def test_generation_slot_applies_the_per_address_limit(services: Services) -> None:
    services.planner_limiter = RateLimiter(1)
    async with ai.generation_slot(fake_request(host="198.51.100.1"), services):
        pass

    with pytest.raises(RateLimitedError, match="address"):
        async with ai.generation_slot(fake_request(host="198.51.100.1"), services):
            pass
    async with ai.generation_slot(fake_request(host="198.51.100.2"), services):
        pass


# Budget reservations


def test_generation_reservation_charges_every_input_byte_and_the_full_output_cap(
    services: Services,
) -> None:
    # At 1,000,000 microdollars per million tokens, each bounded token costs one microdollar.
    input_bound = len(b"ab") + len(json.dumps(SCHEMA).encode()) + ai.MESSAGE_FRAMING_TOKENS

    amount = ai.generation_reservation_microusd("a", "b", SCHEMA, 100, services)

    assert amount == input_bound + 100


def test_reservation_rounds_a_fraction_of_a_microdollar_up(services: Services) -> None:
    services.settings = replace(
        services.settings, ai_input_microusd_per_million=1, ai_output_microusd_per_million=1
    )

    assert ai.generation_reservation_microusd("", "", SCHEMA, 1, services) == 1


def test_budget_that_cannot_fund_the_reservation_is_rate_limited(services: Services) -> None:
    services.settings = replace(services.settings, ai_daily_budget_microusd=10)

    with pytest.raises(RateLimitedError, match="budget"):
        ai.reserve_budget(services, 11)
    assert budget_used(services) == 0


def test_budget_without_an_operations_database_is_rate_limited(services: Services) -> None:
    services.operations = None

    with pytest.raises(RateLimitedError, match="budget"):
        ai.reserve_budget(services, 1)


# One OpenAI generation


@pytest.mark.anyio
async def test_openai_json_sends_one_unstored_strict_schema_request(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests = use_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, json=responses_body({"type": "output_text", "text": '{"ok": true}'})
        ),
    )

    text = await ai.openai_json("Do the task.", "question", SCHEMA, "answer", 256, services)

    assert text == '{"ok": true}'
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert str(requests[0].url) == ai.OPENAI_RESPONSES_URL
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    assert body["store"] is False
    assert body["max_output_tokens"] == 256
    assert body["reasoning"] == {"effort": ai.REASONING_EFFORT}
    assert body["text"]["format"] == {
        "type": "json_schema",
        "name": "answer",
        "strict": True,
        "schema": SCHEMA,
    }


@pytest.mark.anyio
async def test_openai_json_reserves_the_budget_before_calling(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_transport(monkeypatch, lambda request: httpx.Response(500))
    expected = ai.generation_reservation_microusd("Do.", "q", SCHEMA, 64, services)

    with pytest.raises(httpx.HTTPStatusError):
        await ai.openai_json("Do.", "q", SCHEMA, "answer", 64, services)

    # A failed call keeps its reservation (spec 8).
    assert budget_used(services) == expected


@pytest.mark.anyio
async def test_openai_json_without_budget_never_calls_the_provider(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    services.settings = replace(services.settings, ai_daily_budget_microusd=1)
    requests = use_transport(monkeypatch, lambda request: httpx.Response(200))

    with pytest.raises(RateLimitedError):
        await ai.openai_json("Do.", "q", SCHEMA, "answer", 64, services)
    assert requests == []


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        pytest.param(
            responses_body({"type": "refusal", "refusal": "I cannot help."}),
            "refused",
            id="refusal",
        ),
        pytest.param(
            responses_body({"type": "output_text", "text": '{"ok"'}, status="incomplete"),
            "incomplete",
            id="incomplete",
        ),
        pytest.param({"status": "completed", "output": []}, "empty", id="no-text"),
    ],
)
@pytest.mark.anyio
async def test_openai_json_distinguishes_refused_incomplete_and_empty_output(
    services: Services,
    monkeypatch: pytest.MonkeyPatch,
    body: dict[str, object],
    reason: str,
) -> None:
    use_transport(monkeypatch, lambda request: httpx.Response(200, json=body))

    with pytest.raises(ai.ProviderOutputError) as raised:
        await ai.openai_json("Do.", "q", SCHEMA, "answer", 64, services)
    assert raised.value.reason == reason


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("refused", "provider_refused"),
        ("incomplete", "provider_incomplete"),
        ("empty", "provider_incomplete"),
    ],
)
def test_provider_failure_maps_to_its_contract_reason(
    failure: ai.ProviderFailure, reason: str
) -> None:
    assert ai.ProviderOutputError(failure).unanswered_reason == reason


# One vector-store search


@pytest.mark.anyio
async def test_vector_search_posts_the_query_to_the_configured_store(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests = use_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, json={"data": [search_hit("power-methodology", "Sentence one.")]}
        ),
    )
    filters = {"type": "eq", "key": "kind", "value": "agency"}

    passages = await ai.openai_vector_search("What is T2M?", STORE_ID, 3, filters, services)

    assert str(requests[0].url) == f"{ai.OPENAI_VECTOR_STORES_URL}/{STORE_ID}/search"
    assert json.loads(requests[0].content) == {
        "query": "What is T2M?",
        "max_num_results": 3,
        "rewrite_query": False,
        "filters": filters,
    }
    assert [passage.source_id for passage in passages] == ["power-methodology"]
    assert passages[0].section_id == "power-methodology-01"
    assert passages[0].text == "Sentence one."
    assert passages[0].file_id == "file-1"
    assert passages[0].score == 0.8
    assert passages[0].content_sha256 == hashlib.sha256(b"Sentence one.").hexdigest()


@pytest.mark.anyio
async def test_vector_search_reserves_its_own_retrieval_charge(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_transport(monkeypatch, lambda request: httpx.Response(200, json={"data": []}))

    passages = await ai.openai_vector_search("q", STORE_ID, 4, None, services)

    assert passages == []
    assert budget_used(services) == SEARCH_PRICE


@pytest.mark.anyio
async def test_vector_search_drops_hits_that_cannot_be_cited(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    hits = [
        search_hit(None, "No source."),
        search_hit("bad id!", "Bad."),
        search_hit("ok", " "),
        search_hit("ok", "No section.", section_id=None),
        search_hit("ok", "Bad section.", section_id="bad section!"),
    ]
    use_transport(monkeypatch, lambda request: httpx.Response(200, json={"data": hits}))

    assert await ai.openai_vector_search("q", STORE_ID, 4, None, services) == []


@pytest.mark.anyio
async def test_vector_search_caps_each_passage(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    long_text = "A short sentence. " * 200
    use_transport(
        monkeypatch,
        lambda request: httpx.Response(200, json={"data": [search_hit("src", long_text)]}),
    )

    (passage,) = await ai.openai_vector_search("q", STORE_ID, 1, None, services)

    assert len(passage.text) <= ai.PASSAGE_MAX_LENGTH
    assert passage.text.endswith("sentence.")


@pytest.mark.parametrize(
    ("store_id", "max_results", "price"),
    [
        pytest.param("../files", 4, SEARCH_PRICE, id="invalid-store-id"),
        pytest.param(STORE_ID, 5, SEARCH_PRICE, id="too-many-passages"),
        pytest.param(STORE_ID, 0, SEARCH_PRICE, id="no-passages"),
        pytest.param(STORE_ID, 4, 0, id="no-price"),
    ],
)
@pytest.mark.anyio
async def test_vector_search_refuses_an_invalid_configuration_without_calling(
    services: Services,
    monkeypatch: pytest.MonkeyPatch,
    store_id: str,
    max_results: int,
    price: int,
) -> None:
    services.settings = replace(services.settings, rag_search_microusd_per_call=price)
    requests = use_transport(monkeypatch, lambda request: httpx.Response(200, json={"data": []}))

    with pytest.raises(AiUnavailableError):
        await ai.openai_vector_search("q", store_id, max_results, None, services)
    assert requests == []
    assert budget_used(services) == 0


# Citations


def _document(section_id: str = "power-methodology-01") -> DocumentSource:
    return DocumentSource(
        source_id="power-methodology",
        section_id=section_id,
        publisher="NASA Langley Research Center, POWER Project",
        title="POWER Methodology",
        url="https://power.larc.nasa.gov/docs/methodology/",
        section="Meteorology",
        accessed=TODAY,
        sha256="b" * 64,
        kind="agency",
    )


def _retrieved(text: str = "Sentence one.") -> RetrievedPassage:
    return RetrievedPassage(
        source_id="power-methodology",
        section_id="power-methodology-01",
        text=text,
        file_id="file-1",
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        score=0.8,
    )


def test_citation_takes_its_section_from_the_manifest_and_its_text_from_the_passage() -> None:
    cited = ai.citation(_retrieved(), _document())

    assert cited.section_id == "power-methodology-01"
    assert cited.section == "Meteorology"
    assert cited.url == "https://power.larc.nasa.gov/docs/methodology/"
    assert cited.passage == "Sentence one."


def test_citation_refuses_a_manifest_section_of_another_passage() -> None:
    with pytest.raises(ValueError, match="does not match"):
        ai.citation(_retrieved(), _document(section_id="power-methodology-02"))


# Passage caps


def test_short_passage_is_kept_whole() -> None:
    assert ai.cap_passage("  One sentence.  ") == "One sentence."


def test_long_passage_is_cut_after_the_last_sentence_that_fits() -> None:
    text = "First sentence here. Second sentence is longer. Third one never fits."

    assert ai.cap_passage(text, limit=50) == "First sentence here. Second sentence is longer."


def test_passage_without_a_late_sentence_end_is_cut_at_a_space() -> None:
    text = "Short. " + "word " * 20

    assert ai.cap_passage(text, limit=40) == "Short. word word word word word word"


def test_passage_without_spaces_is_cut_at_the_limit() -> None:
    assert ai.cap_passage("x" * 50, limit=10) == "x" * 10
