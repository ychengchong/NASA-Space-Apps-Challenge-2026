"""The chat adapter (spec 8; spec 10, "Chat request and stream").

The real Anthropic SDK runs against `httpx2.MockTransport`, which plays scripted Messages API
replies, so the SDK's tool runner and stream parser are exercised without the network. The SDK
is built on httpx2 and rejects a client from the httpx package.
"""

import dataclasses
import json
import logging
import re
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import anthropic
import httpx
import httpx2
import pytest
from fastapi import FastAPI

from app.adapters.chat import (
    AI_CUT_OFF_MESSAGE,
    AI_FAILED_MESSAGE,
    AI_REFUSED_MESSAGE,
    AI_STEP_LIMIT_MESSAGE,
    AI_TOO_LONG_MESSAGE,
    BODY_TOO_LARGE_MESSAGE,
    CURRENT_CASE_INTRO,
    DAILY_TURNS_COUNTER,
    FALLBACK_BETA,
    MAX_BODY_BYTES,
    MAX_CASE_CHARS,
    MAX_MESSAGE_CHARS,
    MAX_MESSAGES,
    TOOL_FAILED_MESSAGE,
    TOOL_SPECS,
    ChatBackend,
    router,
    unverified_numbers,
)
from app.cache import Cache
from app.config import Settings
from app.models import MAX_COMPARE_PLACES, MIN_COMPARE_PLACES, PLACE_NAME_MAX_LENGTH
from app.ratelimit import RateLimiter
from app.services import Services
from app.sources.base import PointSeries
from app.tools.places import MAX_PLACE_CANDIDATES
from app.tools.trends import MAX_BOX_SIDE_DEGREES, MIN_BOX_SIDE_DEGREES
from tests.fake_source import FakeSource, line, monthly_from_yearly

pytestmark = pytest.mark.anyio

TODAY = date(2026, 11, 13)  # the last complete year is then 2025
RISING = monthly_from_yearly(line(0.05))  # Sen's slope 0.5 per decade from 1981 to 2025
NAIROBI = {"lat": -1.2833, "lon": 36.8167, "name": "Nairobi"}
HELSINKI_CASE = "v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual"
QUESTION = {"messages": [{"role": "user", "text": "Is Nairobi getting warmer?"}]}
MINUS_SIGN = "\u2212"  # typographic minus, as a model may write it
CHAT_LOGGER = "app.adapters.chat"

BASE_SETTINGS = Settings(
    anthropic_api_key="test-key",
    ai_enabled=True,
    ai_model="claude-opus-5-5",
    ai_max_iterations=6,
    ai_max_turns=20,
    ai_daily_turns=500,
    ai_rate_per_minute=10,
    rate_limit_per_minute=120,
    public_base_url=None,
    cache_path=Path("unused.sqlite"),
)

Event = tuple[str, dict[str, Any]]
Reply = list[dict[str, Any]] | httpx2.Response


# Scripted Messages API replies, as server-sent events


def _message_start(message_id: str) -> dict[str, Any]:
    return {
        "type": "message_start",
        "message": {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 1},
        },
    }


def _message_end(stop_reason: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": 5},
        },
        {"type": "message_stop"},
    ]


def _text_block(index: int, *chunks: str) -> list[dict[str, Any]]:
    deltas = [
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "text_delta", "text": chunk},
        }
        for chunk in chunks
    ]
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "text", "text": ""},
        },
        *deltas,
        {"type": "content_block_stop", "index": index},
    ]


def _tool_use_block(
    index: int, tool_use_id: str, name: str, inp: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "tool_use", "id": tool_use_id, "name": name, "input": {}},
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "input_json_delta", "partial_json": json.dumps(inp)},
        },
        {"type": "content_block_stop", "index": index},
    ]


def _thinking_block(index: int, thinking: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "thinking", "thinking": "", "signature": ""},
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "thinking_delta", "thinking": thinking},
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "signature_delta", "signature": "signature"},
        },
        {"type": "content_block_stop", "index": index},
    ]


def tool_use_reply(message_id: str, tool_use_id: str, name: str, inp: Mapping[str, Any]) -> Reply:
    return [
        _message_start(message_id),
        *_tool_use_block(0, tool_use_id, name, inp),
        *_message_end("tool_use"),
    ]


def text_reply(message_id: str, *chunks: str) -> Reply:
    return [_message_start(message_id), *_text_block(0, *chunks), *_message_end("end_turn")]


def text_and_tool_use_reply(
    message_id: str, text: str, tool_use_id: str, name: str, inp: Mapping[str, Any]
) -> Reply:
    """A note written before a tool call, in the same reply."""
    return [
        _message_start(message_id),
        *_text_block(0, text),
        *_tool_use_block(1, tool_use_id, name, inp),
        *_message_end("tool_use"),
    ]


def _unfinished_text(message_id: str, text: str) -> list[dict[str, Any]]:
    """The start of a reply: one text delta, and neither the block nor the message finished."""
    return [_message_start(message_id), *_text_block(0, text)[:-1]]


def cut_off_reply(message_id: str, text: str) -> Reply:
    """A reply whose body ends cleanly before the message is finished."""
    return _unfinished_text(message_id, text)


def refusal_reply(message_id: str) -> Reply:
    return [_message_start(message_id), *_message_end("refusal")]


def empty_reply() -> Reply:
    """A successful reply whose stream body holds no event at all."""
    return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=b"")


def server_error() -> Reply:
    return httpx2.Response(
        500, json={"type": "error", "error": {"type": "api_error", "message": "Internal error"}}
    )


def _sse_body(events: Sequence[Mapping[str, Any]]) -> bytes:
    return "".join(
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
    ).encode()


class _LostConnectionStream(httpx2.AsyncByteStream):
    """A reply body that sends `events`, then fails as a read timeout or a dropped connection
    does while the answer streams.
    """

    def __init__(self, events: Sequence[Mapping[str, Any]]) -> None:
        self._events = events

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield _sse_body(self._events)
        raise httpx2.ReadTimeout("No data arrived within the timeout.")


def connection_lost_reply(message_id: str, text: str) -> Reply:
    """A reply whose connection fails before the message is finished."""
    return httpx2.Response(
        200,
        headers={"content-type": "text/event-stream"},
        stream=_LostConnectionStream(_unfinished_text(message_id, text)),
    )


class FakeClaude:
    """Answers each Messages API request with the next scripted reply and records the request."""

    def __init__(self, *replies: Reply) -> None:
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self.headers: list[httpx2.Headers] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(json.loads(request.content))
        self.headers.append(request.headers)
        reply = self._replies.pop(0)
        if isinstance(reply, httpx2.Response):
            return reply
        return httpx2.Response(
            200, headers={"content-type": "text/event-stream"}, content=_sse_body(reply)
        )


# The app under test


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[Cache]:
    opened = Cache(tmp_path / "cache.sqlite")
    yield opened
    opened.close()


@pytest.fixture
async def anthropic_clients() -> AsyncIterator[list[anthropic.AsyncAnthropic]]:
    """The clients a test creates, closed when it ends."""
    clients: list[anthropic.AsyncAnthropic] = []
    yield clients
    for client in clients:
        await client.close()


def claude_client(
    claude: FakeClaude, clients: list[anthropic.AsyncAnthropic]
) -> anthropic.AsyncAnthropic:
    client = anthropic.AsyncAnthropic(
        api_key="test",
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(claude.handle)),
    )
    clients.append(client)
    return client


class BrokenSource(FakeSource):
    """A source that fails with an error the tool layer does not expect."""

    async def point_series(
        self, lat: float, lon: float, codes: Sequence[str], end_year: int
    ) -> dict[str, PointSeries]:
        raise RuntimeError("broken source: secret words")


def chat_app(
    claude: FakeClaude,
    cache: Cache,
    clients: list[anthropic.AsyncAnthropic],
    source: FakeSource | None = None,
    **settings: Any,
) -> FastAPI:
    resolved = dataclasses.replace(BASE_SETTINGS, **settings)
    services = Services(
        settings=resolved,
        cache=cache,
        source=source if source is not None else FakeSource(RISING),
        today=lambda: TODAY,
    )
    app = FastAPI()
    app.include_router(router)
    app.state.chat_backend = ChatBackend(
        services=services,
        limiter=RateLimiter(resolved.ai_rate_per_minute, clock=lambda: 0.0),
        client=claude_client(claude, clients),
    )
    return app


async def post_chat(app: FastAPI, body: Mapping[str, Any]) -> httpx.Response:
    return await send_chat(app, json=body)


async def send_chat(app: FastAPI, **request: Any) -> httpx.Response:
    """POST /api/chat from a fixed address; `request` holds httpx's body and header arguments."""
    transport = httpx.ASGITransport(app=app, client=("203.0.113.7", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        return await http.post("/api/chat", **request)


async def counted_chunks(chunk: bytes, count: int, sent: list[int]) -> AsyncIterator[bytes]:
    """A streamed body of `count` chunks; `sent` records the size of each chunk the server read."""
    for _ in range(count):
        sent.append(len(chunk))
        yield chunk


def parse_events(text: str) -> list[Event]:
    events: list[Event] = []
    for block in text.strip().split("\n\n"):
        name_line, data_line = block.split("\n")
        events.append(
            (name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: ")))
        )
    return events


def names(events: Sequence[Event]) -> list[str]:
    return [name for name, _ in events]


def steps(events: Sequence[Event]) -> list[tuple[str, str, str]]:
    return [
        (data["tool"], data["label"], data["status"]) for name, data in events if name == "step"
    ]


def last_tool_result(request: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = request["messages"][-1]["content"][0]
    assert result["type"] == "tool_result"
    return result


NAIROBI_TURN = (
    tool_use_reply("msg_1", "toolu_1", "find_place", {"query": "Nairobi"}),
    tool_use_reply("msg_2", "toolu_2", "analyze_trend", {"variable": "air_temp", "place": NAIROBI}),
    text_reply(
        "msg_3",
        "Air temperature in Nairobi rose by about 0.5 °C per decade ",
        "from 1981 to 2025. That is 2.2 °C in total.",
    ),
)


# One turn (spec 8, "One turn"; spec 10, "Chat request and stream")


async def test_turn_streams_steps_then_case_then_text_then_check_and_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(*NAIROBI_TURN), cache, anthropic_clients)

    response = await post_chat(app, QUESTION)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_events(response.text)
    assert names(events) == [
        "step",
        "step",
        "step",
        "step",
        "case",
        "text",
        "text",
        "check",
        "done",
    ]
    assert steps(events) == [
        ("find_place", "Looked up places matching 'Nairobi'", "started"),
        ("find_place", "Looked up places matching 'Nairobi'", "finished"),
        ("analyze_trend", "Tested air temperature in Nairobi, 1981 to 2025", "started"),
        ("analyze_trend", "Tested air temperature in Nairobi, 1981 to 2025", "finished"),
    ]


async def test_each_tool_call_has_its_own_step_id(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(*NAIROBI_TURN), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    ids = [data["id"] for name, data in events if name == "step"]
    assert ids[0] == ids[1]
    assert ids[2] == ids[3]
    assert ids[0] != ids[2]


async def test_case_event_carries_the_investigation(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(*NAIROBI_TURN), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    investigation = next(data for name, data in events if name == "case")["investigation"]
    assert investigation["requested"] == {"from": 1981, "to": 2025, "season": "annual"}
    assert investigation["results"][0]["place"]["name"] == "Nairobi"
    assert investigation["results"][0]["trend"]["sen_slope"] == pytest.approx(0.5)


async def test_text_deltas_arrive_as_written_and_numbers_from_the_tools_pass(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(*NAIROBI_TURN), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert [data["delta"] for name, data in events if name == "text"] == [
        "Air temperature in Nairobi rose by about 0.5 °C per decade ",
        "from 1981 to 2025. That is 2.2 °C in total.",
    ]
    assert events[-2] == ("check", {"unverified": []})


async def test_text_written_before_a_tool_call_is_set_apart_from_the_answer(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(
        text_and_tool_use_reply(
            "msg_1", "Let me look up Nairobi.", "toolu_1", "find_place", {"query": "Nairobi"}
        ),
        text_reply("msg_2", "Air temperature in Nairobi rose."),
    )
    app = chat_app(claude, cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert "".join(data["delta"] for name, data in events if name == "text") == (
        "Let me look up Nairobi.\n\nAir temperature in Nairobi rose."
    )


async def test_number_opening_a_later_text_block_is_checked(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(
        text_and_tool_use_reply(
            "msg_1", "Let me check.", "toolu_1", "find_place", {"query": "Nairobi"}
        ),
        text_reply("msg_2", "9.7 °C per decade is the rate in Nairobi."),
    )
    app = chat_app(claude, cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events[-2] == ("check", {"unverified": ["9.7"]})


async def test_tool_results_go_back_to_the_model_as_json(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(*NAIROBI_TURN)
    app = chat_app(claude, cache, anthropic_clients)

    await post_chat(app, QUESTION)

    places = json.loads(last_tool_result(claude.requests[1])["content"])
    investigation = json.loads(last_tool_result(claude.requests[2])["content"])
    assert places[0]["name"] == "Nairobi"
    assert investigation["requested"]["from"] == 1981


async def test_request_offers_the_five_tools_but_never_get_series(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients)

    await post_chat(app, QUESTION)

    assert [tool["name"] for tool in claude.requests[0]["tools"]] == [
        "search_variables",
        "find_place",
        "analyze_trend",
        "compare_places",
        "map_trends",
    ]


def _schema_nodes(schema: Any) -> Iterator[dict[str, Any]]:
    if isinstance(schema, dict):
        yield schema
        for value in schema.values():
            yield from _schema_nodes(value)
    elif isinstance(schema, list):
        for item in schema:
            yield from _schema_nodes(item)


@pytest.mark.parametrize("spec", TOOL_SPECS, ids=lambda spec: spec.name)
def test_tool_schemas_are_strict(spec: Any) -> None:
    definition = spec.definition()

    assert definition["strict"] is True
    for node in _schema_nodes(definition["input_schema"]):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
        assert not {"minimum", "maximum", "minLength", "maxLength", "minItems"} & node.keys()


@pytest.mark.parametrize(
    ("tool", "limit"),
    [
        ("find_place", f"up to {MAX_PLACE_CANDIDATES} candidates"),
        ("analyze_trend", f"{PLACE_NAME_MAX_LENGTH} characters at most"),
        ("compare_places", f"at {MIN_COMPARE_PLACES} to {MAX_COMPARE_PLACES} places"),
        ("map_trends", f"from {MIN_BOX_SIDE_DEGREES:g} to {MAX_BOX_SIDE_DEGREES:g} degrees"),
        ("map_trends", "south below north and west below east"),
    ],
)
def test_tool_description_states_the_limit_the_tool_enforces(tool: str, limit: str) -> None:
    spec = next(spec for spec in TOOL_SPECS if spec.name == tool)

    assert limit in spec.definition()["description"]


@pytest.mark.parametrize(
    ("tool", "field"), [("search_variables", "region_types"), ("find_place", "region_type")]
)
def test_tool_description_names_the_region_field_its_results_carry(tool: str, field: str) -> None:
    spec = next(spec for spec in TOOL_SPECS if spec.name == tool)

    assert re.search(rf"\b{field}\b", spec.definition()["description"])


def test_find_place_description_says_a_megacity_carries_a_region_type() -> None:
    spec = next(spec for spec in TOOL_SPECS if spec.name == "find_place")

    assert re.search(r"\bmegacity\b", spec.definition()["description"])


def test_period_travels_as_from_in_tool_schemas() -> None:
    analyze = next(spec for spec in TOOL_SPECS if spec.name == "analyze_trend")

    properties = analyze.definition()["input_schema"]["properties"]

    assert "from" in properties
    assert "from_" not in properties


async def test_request_uses_the_model_low_effort_caching_and_the_refusal_fallback(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients, ai_model="claude-test-model")

    await post_chat(app, QUESTION)

    request = claude.requests[0]
    assert request["model"] == "claude-test-model"
    assert request["output_config"] == {"effort": "low"}
    assert "thinking" not in request
    assert "tool_choice" not in request
    assert request["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert request["cache_control"] == {"type": "ephemeral"}
    assert request["fallbacks"] == "default"
    assert FALLBACK_BETA in claude.headers[0]["anthropic-beta"]


async def test_system_prompt_lists_the_catalogue(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients)

    await post_chat(app, QUESTION)

    system_text = claude.requests[0]["system"][-1]["text"]
    assert "- air_temp: Air temperature (°C)" in system_text
    assert "- cloud_cover: Cloud cover (%)" in system_text


async def system_text_sent(cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]) -> str:
    """The system prompt of a turn's first request to the model."""
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    await post_chat(chat_app(claude, cache, anthropic_clients), QUESTION)
    text: str = claude.requests[0]["system"][-1]["text"]
    return text


async def test_system_prompt_asks_for_a_decimal_point_never_a_decimal_comma(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    # The number check reads a comma only as a thousands separator (spec 8, "The number check").
    system_text = await system_text_sent(cache, anthropic_clients)

    assert "- Write decimals with a point, never a decimal comma" in system_text


async def test_system_prompt_asks_to_end_with_one_cross_check_labelled_as_a_suggestion(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    system_text = await system_text_sent(cache, anthropic_clients)

    assert "- End with one suggested cross-check" in system_text
    assert 'Label it "Suggestion"' in system_text


async def test_earlier_turns_are_resent_as_plain_text_only(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients)
    body = {
        "messages": [
            {"role": "user", "text": "Is Nairobi getting warmer?"},
            {"role": "assistant", "text": "Yes, it is."},
            {"role": "user", "text": "And Helsinki?"},
        ]
    }

    await post_chat(app, body)

    assert claude.requests[0]["messages"] == [
        {"role": "user", "content": "Is Nairobi getting warmer?"},
        {"role": "assistant", "content": "Yes, it is."},
        {"role": "user", "content": [{"type": "text", "text": "And Helsinki?"}]},
    ]


async def test_current_case_is_recomputed_and_sent_before_the_question(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients)

    await post_chat(app, {**QUESTION, "case": HELSINKI_CASE})

    case_block, question_block = claude.requests[0]["messages"][-1]["content"]
    intro, case_json = case_block["text"].split("\n", 1)
    assert intro == CURRENT_CASE_INTRO
    assert json.loads(case_json)["results"][0]["place"]["name"] == "Helsinki"
    assert question_block == {"type": "text", "text": "Is Nairobi getting warmer?"}


async def test_numbers_from_the_current_case_pass_and_invented_ones_are_flagged(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    reply = text_reply("msg_1", "In Helsinki it rose 0.50 °C per decade, about 3.7 in all.")
    app = chat_app(FakeClaude(reply), cache, anthropic_clients)

    events = parse_events((await post_chat(app, {**QUESTION, "case": HELSINKI_CASE})).text)

    assert events[-2] == ("check", {"unverified": ["3.7"]})


async def test_unreadable_case_is_left_out(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients)

    response = await post_chat(app, {**QUESTION, "case": "v=air_temp"})

    assert names(parse_events(response.text))[-1] == "done"
    assert claude.requests[0]["messages"][-1]["content"] == [
        {"type": "text", "text": "Is Nairobi getting warmer?"}
    ]


async def test_compare_step_names_every_place(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    helsinki = {"lat": 60.17, "lon": 24.94, "name": "Helsinki"}
    compare = {"variable": "precipitation", "places": [helsinki, NAIROBI], "from": 1991}
    claude = FakeClaude(
        tool_use_reply("msg_1", "toolu_1", "compare_places", compare),
        text_reply("msg_2", "Done."),
    )
    app = chat_app(claude, cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert steps(events)[0] == (
        "compare_places",
        "Compared precipitation in Helsinki and Nairobi, 1991 to 2025",
        "started",
    )


# Tool errors


async def test_tool_error_marks_the_step_failed_and_returns_an_error_result(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    unknown = {"variable": "sea_level", "place": NAIROBI}
    claude = FakeClaude(
        tool_use_reply("msg_1", "toolu_1", "analyze_trend", unknown),
        text_reply("msg_2", "That variable is not in the catalogue."),
    )
    app = chat_app(claude, cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert steps(events) == [
        ("analyze_trend", "Tested 'sea_level' in Nairobi", "started"),
        ("analyze_trend", "Tested 'sea_level' in Nairobi", "failed"),
    ]
    assert last_tool_result(claude.requests[1]) == {
        "type": "tool_result",
        "tool_use_id": "toolu_1",
        "content": "'sea_level' is not a variable in the catalogue.",
        "is_error": True,
    }


async def test_tool_input_the_model_cannot_use_returns_an_error_result(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    one_place = {"variable": "air_temp", "places": [NAIROBI]}
    claude = FakeClaude(
        tool_use_reply("msg_1", "toolu_1", "compare_places", one_place),
        text_reply("msg_2", "I need two places."),
    )
    app = chat_app(claude, cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert steps(events) == [
        ("compare_places", "Compared places", "started"),
        ("compare_places", "Compared places", "failed"),
    ]
    result = last_tool_result(claude.requests[1])
    assert result["is_error"] is True
    assert result["content"].startswith("The input is not valid: places")


# With BrokenSource, analyze_trend fails with an error the tool layer does not expect.
BROKEN_TOOL_TURN = (
    tool_use_reply("msg_1", "toolu_1", "analyze_trend", {"variable": "air_temp", "place": NAIROBI}),
    text_reply("msg_2", "The data could not be read just now."),
)


async def test_unexpected_tool_failure_returns_a_plain_error_result(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(*BROKEN_TOOL_TURN)
    app = chat_app(claude, cache, anthropic_clients, source=BrokenSource(RISING))

    await post_chat(app, QUESTION)

    assert last_tool_result(claude.requests[1]) == {
        "type": "tool_result",
        "tool_use_id": "toolu_1",
        "content": TOOL_FAILED_MESSAGE,
        "is_error": True,
    }


async def test_unexpected_tool_failure_is_logged_by_its_error_class_only(
    cache: Cache,
    anthropic_clients: list[anthropic.AsyncAnthropic],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    claude = FakeClaude(*BROKEN_TOOL_TURN)
    app = chat_app(claude, cache, anthropic_clients, source=BrokenSource(RISING))

    await post_chat(app, QUESTION)

    assert [record for record in caplog.records if record.exc_info is not None] == []
    assert [record.getMessage() for record in caplog.records if record.name == CHAT_LOGGER] == [
        "Tool analyze_trend failed unexpectedly with RuntimeError"
    ]
    assert "secret" not in caplog.text


async def test_unexpected_tool_failure_marks_the_step_failed_and_the_turn_goes_on(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(*BROKEN_TOOL_TURN)
    app = chat_app(claude, cache, anthropic_clients, source=BrokenSource(RISING))

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert [status for _, _, status in steps(events)] == ["started", "failed"]
    assert names(events)[-2:] == ["check", "done"]


# A turn that ends without an answer


async def test_refusal_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(refusal_reply("msg_1")), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events == [
        ("error", {"code": "ai_unavailable", "message": AI_REFUSED_MESSAGE}),
        ("done", {}),
    ]


async def test_cut_off_answer_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    reply = [
        _message_start("msg_1"),
        *_text_block(0, "Air temperature in"),
        *_message_end("max_tokens"),
    ]
    app = chat_app(FakeClaude(reply), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events[-2:] == [
        ("error", {"code": "ai_unavailable", "message": AI_CUT_OFF_MESSAGE}),
        ("done", {}),
    ]


async def test_conversation_too_long_for_the_model_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    reply = [_message_start("msg_1"), *_message_end("model_context_window_exceeded")]
    app = chat_app(FakeClaude(reply), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events == [
        ("error", {"code": "ai_unavailable", "message": AI_TOO_LONG_MESSAGE}),
        ("done", {}),
    ]


async def test_reply_cut_off_before_message_stop_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(cut_off_reply("msg_1", "Air ")), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events == [
        ("text", {"delta": "Air "}),
        ("error", {"code": "ai_unavailable", "message": AI_FAILED_MESSAGE}),
        ("done", {}),
    ]


async def test_unknown_stop_reason_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    reply = [_message_start("msg_1"), *_text_block(0, "Hello."), *_message_end("future_reason")]
    app = chat_app(FakeClaude(reply), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events[-2:] == [
        ("error", {"code": "ai_unavailable", "message": AI_FAILED_MESSAGE}),
        ("done", {}),
    ]


async def test_connection_lost_mid_answer_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(connection_lost_reply("msg_1", "Air ")), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events == [
        ("text", {"delta": "Air "}),
        ("error", {"code": "ai_unavailable", "message": AI_FAILED_MESSAGE}),
        ("done", {}),
    ]


async def test_thinking_never_reaches_the_stream(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    reply = [
        _message_start("msg_1"),
        *_thinking_block(0, "Private reasoning."),
        *_text_block(1, "Hello."),
        *_message_end("end_turn"),
    ]
    app = chat_app(FakeClaude(reply), cache, anthropic_clients)

    response = await post_chat(app, QUESTION)

    assert "Private reasoning" not in response.text
    assert names(parse_events(response.text)) == ["text", "check", "done"]


async def test_api_error_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(server_error()), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert names(events) == ["error", "done"]
    assert events[0][1]["code"] == "ai_unavailable"


async def test_empty_reply_body_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(empty_reply()), cache, anthropic_clients)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert events == [
        ("error", {"code": "ai_unavailable", "message": AI_FAILED_MESSAGE}),
        ("done", {}),
    ]


async def test_empty_reply_body_is_logged_by_its_error_class_only(
    cache: Cache,
    anthropic_clients: list[anthropic.AsyncAnthropic],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=CHAT_LOGGER)
    app = chat_app(FakeClaude(empty_reply()), cache, anthropic_clients)

    await post_chat(app, QUESTION)

    records = [record for record in caplog.records if record.name == CHAT_LOGGER]
    assert [(record.getMessage(), record.exc_info) for record in records] == [
        ("AI call failed with AssertionError", None)
    ]


async def test_unexpected_failure_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients, source=BrokenSource(RISING))

    events = parse_events((await post_chat(app, {**QUESTION, "case": HELSINKI_CASE})).text)

    assert events == [
        ("error", {"code": "ai_unavailable", "message": AI_FAILED_MESSAGE}),
        ("done", {}),
    ]


async def test_unexpected_failure_is_logged_by_its_error_class_only(
    cache: Cache,
    anthropic_clients: list[anthropic.AsyncAnthropic],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=CHAT_LOGGER)
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients, source=BrokenSource(RISING))

    await post_chat(app, {**QUESTION, "case": HELSINKI_CASE})

    records = [record for record in caplog.records if record.name == CHAT_LOGGER]
    assert [(record.getMessage(), record.exc_info) for record in records] == [
        ("AI turn failed unexpectedly with RuntimeError", None)
    ]
    assert "secret" not in caplog.text


async def test_iteration_limit_ends_with_an_error_then_done(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(
        tool_use_reply("msg_1", "toolu_1", "find_place", {"query": "Nairobi"}),
        tool_use_reply("msg_2", "toolu_2", "find_place", {"query": "Nairobi"}),
        text_reply("msg_3", "Never sent."),
    )
    app = chat_app(claude, cache, anthropic_clients, ai_max_iterations=2)

    events = parse_events((await post_chat(app, QUESTION)).text)

    assert len(claude.requests) == 2
    assert names(events) == ["step", "step", "step", "step", "error", "done"]
    assert events[-2][1] == {"code": "ai_unavailable", "message": AI_STEP_LIMIT_MESSAGE}


# Refused before the stream (spec 8, "Limits"; spec 10, "Errors")


async def test_disabled_ai_answers_503_without_calling_the_model(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude()
    app = chat_app(claude, cache, anthropic_clients, ai_enabled=False)

    response = await post_chat(app, QUESTION)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"
    assert claude.requests == []


async def test_missing_key_answers_503(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(), cache, anthropic_clients, anthropic_api_key=None)

    response = await post_chat(app, QUESTION)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"


async def test_too_many_turns_per_minute_from_one_address_answers_429(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude(text_reply("msg_1", "Hello."))
    app = chat_app(claude, cache, anthropic_clients, ai_rate_per_minute=1)

    first = await post_chat(app, QUESTION)
    second = await post_chat(app, QUESTION)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"


async def test_daily_cap_survives_a_restart(
    tmp_path: Path, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    path = tmp_path / "counters.sqlite"
    first_cache = Cache(path)
    first_app = chat_app(
        FakeClaude(text_reply("msg_1", "Hello.")), first_cache, anthropic_clients, ai_daily_turns=1
    )
    assert (await post_chat(first_app, QUESTION)).status_code == 200
    first_cache.close()

    reopened = Cache(path)
    try:
        app = chat_app(FakeClaude(), reopened, anthropic_clients, ai_daily_turns=1)
        response = await post_chat(app, QUESTION)
    finally:
        reopened.close()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"


async def test_daily_cap_counts_each_day_apart(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    cache.increment_counter(DAILY_TURNS_COUNTER, "2026-11-12")
    app = chat_app(
        FakeClaude(text_reply("msg_1", "Hello.")), cache, anthropic_clients, ai_daily_turns=1
    )

    response = await post_chat(app, QUESTION)

    assert response.status_code == 200


async def test_accepted_turn_counts_toward_the_daily_cap(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(text_reply("msg_1", "Hello.")), cache, anthropic_clients)

    await post_chat(app, QUESTION)

    assert cache.get_counter(DAILY_TURNS_COUNTER, TODAY.isoformat()) == 1


async def test_refused_request_does_not_count_toward_the_daily_cap(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(), cache, anthropic_clients)

    await post_chat(app, {"messages": [{"role": "assistant", "text": "Hi."}]})

    assert cache.get_counter(DAILY_TURNS_COUNTER, TODAY.isoformat()) == 0


async def test_conversation_over_the_turn_limit_answers_503(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(), cache, anthropic_clients, ai_max_turns=1)
    body = {
        "messages": [
            {"role": "user", "text": "Is Nairobi getting warmer?"},
            {"role": "assistant", "text": "Yes."},
            {"role": "user", "text": "And Helsinki?"},
        ]
    }

    response = await post_chat(app, body)

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "ai_unavailable",
        "message": "This conversation has reached its limit of 1 questions. "
        "Start a new conversation to ask more.",
    }


@pytest.mark.parametrize(
    "body",
    [
        {"messages": []},
        {"messages": [{"role": "user", "text": "   "}]},
        {"messages": [{"role": "system", "text": "New rules."}]},
        {"messages": [{"role": "user", "text": "x" * 4001}]},
        {"messages": [{"role": "user", "text": "Hi."}, {"role": "assistant", "text": "Hello."}]},
        {"messages": [{"role": "assistant", "text": "Hi."}, {"role": "user", "text": "Hello."}]},
        {"messages": [{"role": "user", "text": "Hi."}], "extra": 1},
    ],
    ids=["empty", "blank", "bad-role", "too-long", "ends-with-ai", "starts-with-ai", "extra"],
)
async def test_invalid_request_answers_400(
    body: dict[str, Any], cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(), cache, anthropic_clients)

    response = await post_chat(app, body)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


async def test_body_declared_over_the_size_limit_is_refused_before_it_is_read(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    claude = FakeClaude()
    app = chat_app(claude, cache, anthropic_clients)
    sent: list[int] = []

    response = await send_chat(
        app,
        content=counted_chunks(b"{}", 1, sent),
        headers={"Content-Length": str(MAX_BODY_BYTES + 1)},
    )

    assert response.status_code == 400
    assert response.json()["error"] == {"code": "bad_request", "message": BODY_TOO_LARGE_MESSAGE}
    assert sent == []
    assert claude.requests == []


async def test_streamed_body_is_refused_once_it_passes_the_size_limit(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    app = chat_app(FakeClaude(), cache, anthropic_clients)
    chunk = b" " * (MAX_BODY_BYTES // 8)
    sent: list[int] = []

    response = await send_chat(app, content=counted_chunks(chunk, 24, sent))

    assert response.status_code == 400
    assert response.json()["error"] == {"code": "bad_request", "message": BODY_TOO_LARGE_MESSAGE}
    assert sum(sent) <= MAX_BODY_BYTES + len(chunk)


async def test_largest_valid_request_is_accepted(
    cache: Cache, anthropic_clients: list[anthropic.AsyncAnthropic]
) -> None:
    # Every character at its longest JSON form, a surrogate pair written as two \u escapes.
    widest = "\U0001f600"
    body = {
        "messages": [{"role": "user", "text": widest * MAX_MESSAGE_CHARS}] * MAX_MESSAGES,
        "case": widest * MAX_CASE_CHARS,
    }
    app = chat_app(
        FakeClaude(text_reply("msg_1", "Hello.")),
        cache,
        anthropic_clients,
        ai_max_turns=MAX_MESSAGES,
    )

    response = await send_chat(app, content=json.dumps(body).encode())

    assert response.status_code == 200


# The number check (spec 8, "The number check")


def test_number_matches_a_result_rounded_to_the_digits_written() -> None:
    assert unverified_numbers("about 0.35 or 0.3 or 0.346", [0.3456], []) == []


def test_number_rounded_wrongly_is_flagged() -> None:
    assert unverified_numbers("about 0.34", [0.3456], []) == ["0.34"]


def test_number_matches_either_the_screen_rounding_or_half_up() -> None:
    assert unverified_numbers("0.12 or 0.13", [0.125], []) == []


def test_sign_is_ignored() -> None:
    assert (
        unverified_numbers(f"fell by 0.42, a slope of {MINUS_SIGN}0.42 or -0.42", [-0.42], []) == []
    )


def test_years_inside_a_period_pass() -> None:
    assert unverified_numbers("from 1990 to 2025", [], [(1981, 2025)]) == []


def test_years_outside_every_period_are_flagged() -> None:
    assert unverified_numbers("since 1975 and by 2030", [], [(1981, 2025)]) == ["1975", "2030"]


def test_whole_numbers_up_to_ten_pass() -> None:
    assert unverified_numbers("0, 3 and 10 years, but 11", [], []) == ["11"]


def test_decimal_small_numbers_need_a_match() -> None:
    assert unverified_numbers("about 2.5", [], []) == ["2.5"]


def test_invented_number_is_flagged_as_written() -> None:
    assert unverified_numbers("It rose by +1,234.5 mm.", [0.5], []) == ["+1,234.5"]


def test_thousands_separators_join_one_number() -> None:
    assert unverified_numbers("about 1,234.5 mm", [1234.5], []) == []


def test_numbers_inside_result_strings_count() -> None:
    evidence = [{"verdict": {"sentence": "rose by about 0.35 °C per decade"}}]

    assert unverified_numbers("0.35", evidence, []) == []


def test_each_unverified_number_is_listed_once() -> None:
    assert unverified_numbers("7.25, then 7.25 again", [], []) == ["7.25"]


def test_number_written_with_a_leading_point_is_checked() -> None:
    assert unverified_numbers("about .5, or .3", [0.31], []) == [".5"]


def test_number_written_with_an_exponent_is_checked() -> None:
    assert unverified_numbers("p = 4e-2", [0.5], []) == ["4e-2"]


@pytest.mark.parametrize("written", ["2.5e-11", f"2.5e{MINUS_SIGN}11", "2.5E-11"])
def test_number_with_an_exponent_matches_the_result_it_rounds(written: str) -> None:
    assert unverified_numbers(f"p = {written}", [2.5279878964860453e-11], []) == []


def test_exponent_longer_than_any_float_needs_is_not_read_as_one() -> None:
    assert unverified_numbers("p = 1e-9999", [0.5], []) == ["9999"]


def test_digits_inside_words_are_not_numbers() -> None:
    assert unverified_numbers("CO2 and API v2.10.3", [], []) == []


def test_true_and_false_are_not_numbers() -> None:
    assert unverified_numbers("1.0", [True], []) == ["1.0"]
