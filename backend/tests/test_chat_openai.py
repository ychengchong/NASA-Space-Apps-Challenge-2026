"""The chat adapter on the OpenAI Responses API (spec 8, "The OpenAI path"; spec 10, "Chat
request and stream").

The real OpenAI SDK runs against `httpx2.MockTransport`, which plays scripted Responses API
streams, so the SDK's stream parser and the adapter's tool loop run without the network. The
helpers shared with the Claude tests come from test_chat.py.
"""

import dataclasses
import json
import logging
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import anthropic
import httpx2
import openai
import pytest
from fastapi import FastAPI

from app.adapters.chat import (
    AI_CUT_OFF_MESSAGE,
    AI_FAILED_MESSAGE,
    AI_MAX_TOKENS,
    AI_REFUSED_MESSAGE,
    AI_REQUEST_TIMEOUT_SECONDS,
    AI_STEP_LIMIT_MESSAGE,
    CURRENT_CASE_INTRO,
    SYSTEM_RULES,
    TOOL_FAILED_MESSAGE,
    TOOL_SPECS,
    ChatBackend,
    close_chat_backend,
    create_chat_backend,
    router,
)
from app.cache import Cache
from app.ratelimit import RateLimiter
from app.services import Services
from tests.fake_source import FakeSource
from tests.test_chat import (
    BASE_SETTINGS,
    CHAT_LOGGER,
    HELSINKI_CASE,
    NAIROBI,
    QUESTION,
    RISING,
    TODAY,
    BrokenSource,
    names,
    parse_events,
    post_chat,
    steps,
)

pytestmark = pytest.mark.anyio

OPENAI_LOGGER = "app.adapters.chat_openai"
OPENAI_SETTINGS = dataclasses.replace(
    BASE_SETTINGS,
    ai_provider="openai",
    anthropic_api_key=None,
    openai_api_key="test-key",
    ai_model="gpt-6-luna",
)

Event = dict[str, Any]
Reply = list[Event] | httpx2.Response


# Scripted Responses API streams, as server-sent events


@dataclasses.dataclass(frozen=True)
class Item:
    """One output item of a scripted response: the item as first announced, the events that
    stream its content, and the finished item, as the final response lists it.
    """

    added: Event
    content: list[Event]
    done: Event


def reasoning(item_id: str) -> Item:
    done = {
        "id": item_id,
        "type": "reasoning",
        "summary": [],
        "encrypted_content": f"encrypted-{item_id}",
    }
    # The encrypted content may be incomplete until the item is done.
    return Item(added={"id": item_id, "type": "reasoning", "summary": []}, content=[], done=done)


def _text_part(text: str) -> Event:
    return {"type": "output_text", "text": text, "annotations": []}


def _message_added(item_id: str) -> Event:
    return {
        "id": item_id,
        "type": "message",
        "role": "assistant",
        "status": "in_progress",
        "content": [],
    }


def message(item_id: str, *chunks: str) -> Item:
    text = "".join(chunks)
    deltas = [
        {
            "type": "response.output_text.delta",
            "item_id": item_id,
            "content_index": 0,
            "delta": chunk,
            "logprobs": [],
        }
        for chunk in chunks
    ]
    content = [
        {
            "type": "response.content_part.added",
            "item_id": item_id,
            "content_index": 0,
            "part": _text_part(""),
        },
        *deltas,
        {
            "type": "response.output_text.done",
            "item_id": item_id,
            "content_index": 0,
            "text": text,
            "logprobs": [],
        },
        {
            "type": "response.content_part.done",
            "item_id": item_id,
            "content_index": 0,
            "part": _text_part(text),
        },
    ]
    added = _message_added(item_id)
    done = {**added, "status": "completed", "content": [_text_part(text)]}
    return Item(added=added, content=content, done=done)


def refusal(item_id: str, text: str, *, streamed: bool = True) -> Item:
    """A message that declines. Unless `streamed`, the refusal shows only in the finished item."""
    part = {"type": "refusal", "refusal": text}
    content = [
        {
            "type": "response.content_part.added",
            "item_id": item_id,
            "content_index": 0,
            "part": {"type": "refusal", "refusal": ""},
        },
        {
            "type": "response.refusal.delta",
            "item_id": item_id,
            "content_index": 0,
            "delta": text,
        },
        {
            "type": "response.refusal.done",
            "item_id": item_id,
            "content_index": 0,
            "refusal": text,
        },
        {
            "type": "response.content_part.done",
            "item_id": item_id,
            "content_index": 0,
            "part": part,
        },
    ]
    added = _message_added(item_id)
    done = {**added, "status": "completed", "content": [part]}
    return Item(added=added, content=content if streamed else [], done=done)


def function_call(
    item_id: str | None, call_id: str, name: str, arguments: Mapping[str, Any] | str
) -> Item:
    text = arguments if isinstance(arguments, str) else json.dumps(arguments)
    done = {
        "id": item_id,
        "type": "function_call",
        "status": "completed",
        "call_id": call_id,
        "name": name,
        "arguments": text,
    }
    content = [
        {"type": "response.function_call_arguments.delta", "item_id": item_id, "delta": text},
        {
            "type": "response.function_call_arguments.done",
            "item_id": item_id,
            "name": name,
            "arguments": text,
        },
    ]
    added = {**done, "status": "in_progress", "arguments": ""}
    return Item(added=added, content=content, done=done)


_FINAL_STATUS = {
    "response.completed": "completed",
    "response.incomplete": "incomplete",
    "response.failed": "failed",
}


def _response(
    response_id: str, status: str, output: Sequence[Event], **fields: Any
) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "response",
        "created_at": 1794614400,
        "status": status,
        "model": "gpt-6-luna",
        "output": list(output),
        "error": None,
        "incomplete_details": None,
        "store": False,
        **fields,
    }


def _item_events(items: Sequence[Item]) -> list[Event]:
    events: list[Event] = []
    for index, item in enumerate(items):
        events.append(
            {"type": "response.output_item.added", "output_index": index, "item": item.added}
        )
        events.extend({**event, "output_index": index} for event in item.content)
        events.append(
            {"type": "response.output_item.done", "output_index": index, "item": item.done}
        )
    return events


def reply(
    response_id: str, *items: Item, final: str = "response.completed", **fields: Any
) -> Reply:
    """A response's whole stream. `final` names its last event; `fields` go into the response
    that event carries.
    """
    output = [item.done for item in items]
    return [
        {"type": "response.created", "response": _response(response_id, "in_progress", [])},
        *_item_events(items),
        {"type": final, "response": _response(response_id, _FINAL_STATUS[final], output, **fields)},
    ]


def unfinished_reply(response_id: str, *chunks: str) -> list[Event]:
    """The start of a response: its text deltas, and neither the message nor the response done."""
    item = message(f"msg_{response_id}", *chunks)
    return [
        {"type": "response.created", "response": _response(response_id, "in_progress", [])},
        {"type": "response.output_item.added", "output_index": 0, "item": item.added},
        *({**event, "output_index": 0} for event in item.content[:-2]),
    ]


def function_call_reply(
    response_id: str, call_id: str, name: str, arguments: Mapping[str, Any] | str
) -> Reply:
    """A response that reasons, then calls one function."""
    return reply(
        response_id,
        reasoning(f"rs_{response_id}"),
        function_call(f"fc_{call_id}", call_id, name, arguments),
    )


def text_reply(response_id: str, *chunks: str) -> Reply:
    return reply(response_id, message(f"msg_{response_id}", *chunks))


def _sse_body(events: Sequence[Mapping[str, Any]]) -> bytes:
    return "".join(
        f"event: {event['type']}\ndata: {json.dumps({**event, 'sequence_number': number})}\n\n"
        for number, event in enumerate(events)
    ).encode()


class _LostConnectionStream(httpx2.AsyncByteStream):
    """A reply body that sends `events`, then fails as a read timeout or a dropped connection
    does.
    """

    def __init__(self, events: Sequence[Mapping[str, Any]]) -> None:
        self._events = events

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield _sse_body(self._events)
        raise httpx2.ReadTimeout("No data arrived within the timeout.")


def connection_lost_reply(response_id: str, *chunks: str) -> Reply:
    return httpx2.Response(
        200,
        headers={"content-type": "text/event-stream"},
        stream=_LostConnectionStream(unfinished_reply(response_id, *chunks)),
    )


def server_error() -> Reply:
    return httpx2.Response(
        500, json={"error": {"type": "server_error", "message": "Internal error", "code": None}}
    )


def server_error_whose_body_is_lost() -> Reply:
    return httpx2.Response(500, stream=_LostConnectionStream([]))


class FakeOpenAI:
    """Answers each Responses API request with the next scripted reply and records the request."""

    def __init__(self, *replies: Reply) -> None:
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self.paths: list[str] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(json.loads(request.content))
        self.paths.append(request.url.path)
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
async def openai_clients() -> AsyncIterator[list[openai.AsyncOpenAI]]:
    """The clients a test creates, closed when it ends."""
    clients: list[openai.AsyncOpenAI] = []
    yield clients
    for client in clients:
        await client.close()


def openai_client(fake: FakeOpenAI, clients: list[openai.AsyncOpenAI]) -> openai.AsyncOpenAI:
    client = openai.AsyncOpenAI(
        api_key="test",
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(fake.handle)),
    )
    clients.append(client)
    return client


def chat_app(
    fake: FakeOpenAI,
    cache: Cache,
    clients: list[openai.AsyncOpenAI],
    source: FakeSource | None = None,
    **settings: Any,
) -> FastAPI:
    resolved = dataclasses.replace(OPENAI_SETTINGS, **settings)
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
        client=openai_client(fake, clients),
    )
    return app


async def events_of(app: FastAPI, body: Mapping[str, Any] = QUESTION) -> list[tuple[str, Any]]:
    return parse_events((await post_chat(app, body)).text)


def function_output(request: Mapping[str, Any]) -> dict[str, Any]:
    """The last input item of a request, which must be a function call's output."""
    output: dict[str, Any] = request["input"][-1]
    assert output["type"] == "function_call_output"
    return output


def error_event(message: str) -> tuple[str, dict[str, str]]:
    return ("error", {"code": "ai_unavailable", "message": message})


NAIROBI_TURN = (
    function_call_reply("resp_1", "call_1", "find_place", {"query": "Nairobi"}),
    function_call_reply(
        "resp_2", "call_2", "analyze_trend", {"variable": "air_temp", "place": NAIROBI}
    ),
    text_reply(
        "resp_3",
        "Air temperature in Nairobi rose by about 0.5 °C per decade ",
        "from 1981 to 2025. That is 2.2 °C in total.",
    ),
)


# Choosing the client (spec 11, "Configuration")


def backend_services(cache: Cache, **settings: Any) -> Services:
    resolved = dataclasses.replace(BASE_SETTINGS, **settings)
    return Services(settings=resolved, cache=cache, source=FakeSource(RISING), today=lambda: TODAY)


async def test_backend_on_the_openai_provider_has_an_openai_client_with_the_timeout(
    cache: Cache,
) -> None:
    services = backend_services(
        cache, ai_provider="openai", anthropic_api_key=None, openai_api_key="test-key"
    )

    backend = create_chat_backend(services)
    try:
        assert isinstance(backend.client, openai.AsyncOpenAI)
        assert backend.client.timeout == AI_REQUEST_TIMEOUT_SECONDS
    finally:
        await close_chat_backend(backend)


async def test_backend_on_the_anthropic_provider_has_an_anthropic_client(cache: Cache) -> None:
    services = backend_services(cache, openai_api_key="test-key")

    backend = create_chat_backend(services)
    try:
        assert isinstance(backend.client, anthropic.AsyncAnthropic)
    finally:
        await close_chat_backend(backend)


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param({"ai_enabled": False}, id="ai-disabled"),
        pytest.param({"ai_provider": "openai", "openai_api_key": None}, id="provider-without-key"),
    ],
)
async def test_backend_has_no_client_when_the_ai_is_off(
    cache: Cache, settings: dict[str, Any]
) -> None:
    backend = create_chat_backend(backend_services(cache, **settings))

    assert backend.client is None


async def test_openai_provider_without_its_key_answers_503(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI()
    app = chat_app(fake, cache, openai_clients, openai_api_key=None)

    response = await post_chat(app, QUESTION)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"
    assert fake.requests == []


# One turn (spec 8, "One turn"; spec 10, "Chat request and stream")


async def test_turn_streams_steps_then_case_then_text_then_check_and_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    app = chat_app(FakeOpenAI(*NAIROBI_TURN), cache, openai_clients)

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


async def test_case_event_carries_the_investigation(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    events = await events_of(chat_app(FakeOpenAI(*NAIROBI_TURN), cache, openai_clients))

    investigation = next(data for name, data in events if name == "case")["investigation"]
    assert investigation["requested"] == {"from": 1981, "to": 2025, "season": "annual"}
    assert investigation["results"][0]["place"]["name"] == "Nairobi"
    assert investigation["results"][0]["trend"]["sen_slope"] == pytest.approx(0.5)


async def test_text_deltas_arrive_as_written_and_numbers_from_the_tools_pass(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    events = await events_of(chat_app(FakeOpenAI(*NAIROBI_TURN), cache, openai_clients))

    assert [data["delta"] for name, data in events if name == "text"] == [
        "Air temperature in Nairobi rose by about 0.5 °C per decade ",
        "from 1981 to 2025. That is 2.2 °C in total.",
    ]
    assert events[-2] == ("check", {"unverified": []})


async def test_text_written_before_a_function_call_is_set_apart_from_the_answer(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(
        reply(
            "resp_1",
            message("msg_1", "Let me look up Nairobi."),
            function_call("fc_1", "call_1", "find_place", {"query": "Nairobi"}),
        ),
        text_reply("resp_2", "Air temperature in Nairobi rose."),
    )

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert "".join(data["delta"] for name, data in events if name == "text") == (
        "Let me look up Nairobi.\n\nAir temperature in Nairobi rose."
    )


async def test_numbers_from_the_current_case_pass_and_invented_ones_are_flagged(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(
        text_reply("resp_1", "In Helsinki it rose 0.50 °C per decade, about 3.7 in all.")
    )
    app = chat_app(fake, cache, openai_clients)

    events = await events_of(app, {**QUESTION, "case": HELSINKI_CASE})

    assert events[-2] == ("check", {"unverified": ["3.7"]})


# The requests (spec 8, "The OpenAI path")


async def test_every_request_streams_and_asks_the_api_to_store_nothing(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(*NAIROBI_TURN)

    await post_chat(chat_app(fake, cache, openai_clients), QUESTION)

    assert len(fake.requests) == 3
    assert all(request["stream"] is True for request in fake.requests)
    assert all(request["store"] is False for request in fake.requests)
    assert all(path.endswith("/responses") for path in fake.paths)


async def test_request_uses_the_model_low_reasoning_effort_and_the_output_cap(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(text_reply("resp_1", "Hello."))

    await post_chat(chat_app(fake, cache, openai_clients, ai_model="gpt-test-model"), QUESTION)

    request = fake.requests[0]
    assert request["model"] == "gpt-test-model"
    assert request["reasoning"] == {"effort": "low"}
    assert request["max_output_tokens"] == AI_MAX_TOKENS
    assert "tool_choice" not in request


async def test_instructions_hold_the_rules_and_the_catalogue(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(text_reply("resp_1", "Hello."))

    await post_chat(chat_app(fake, cache, openai_clients), QUESTION)

    instructions = fake.requests[0]["instructions"]
    assert instructions.startswith(SYSTEM_RULES)
    assert "- air_temp: Air temperature (°C)" in instructions
    assert "- cloud_cover: Cloud cover (%)" in instructions


async def test_request_offers_the_five_tools_as_functions_without_strict_mode(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(text_reply("resp_1", "Hello."))

    await post_chat(chat_app(fake, cache, openai_clients), QUESTION)

    tools = fake.requests[0]["tools"]
    assert [tool["name"] for tool in tools] == [
        "search_variables",
        "find_place",
        "analyze_trend",
        "compare_places",
        "map_trends",
    ]
    assert all(tool["type"] == "function" and tool["strict"] is False for tool in tools)


@pytest.mark.parametrize("spec", TOOL_SPECS, ids=lambda spec: spec.name)
def test_function_has_the_description_and_schema_claude_gets(spec: Any) -> None:
    claude = spec.definition()

    function = spec.openai_definition()

    assert function["description"] == claude["description"]
    assert function["parameters"] == claude["input_schema"]


async def test_next_request_resends_the_response_output_then_the_function_output(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    thinking = reasoning("rs_1")
    call = function_call("fc_1", "call_1", "find_place", {"query": "Nairobi"})
    fake = FakeOpenAI(reply("resp_1", thinking, call), text_reply("resp_2", "Hello."))

    await post_chat(chat_app(fake, cache, openai_clients), QUESTION)

    first, second = fake.requests
    turn_so_far = len(first["input"])
    assert second["input"][:turn_so_far] == first["input"]
    resent_thinking, resent_call, output = second["input"][turn_so_far:]
    assert resent_thinking == thinking.done
    assert resent_call == call.done
    assert output["type"] == "function_call_output"
    assert output["call_id"] == "call_1"
    assert json.loads(output["output"])[0]["name"] == "Nairobi"


async def test_function_call_with_a_null_id_is_resent_without_one(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    call = function_call(None, "call_1", "find_place", {"query": "Nairobi"})
    fake = FakeOpenAI(reply("resp_1", call), text_reply("resp_2", "Hello."))

    await post_chat(chat_app(fake, cache, openai_clients), QUESTION)

    resent_call = fake.requests[1]["input"][-2]
    assert resent_call["call_id"] == "call_1"
    assert "id" not in resent_call


async def test_earlier_turns_are_resent_as_plain_text_only(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(text_reply("resp_1", "Hello."))
    body = {
        "messages": [
            {"role": "user", "text": "Is Nairobi getting warmer?"},
            {"role": "assistant", "text": "Yes, it is."},
            {"role": "user", "text": "And Helsinki?"},
        ]
    }

    await post_chat(chat_app(fake, cache, openai_clients), body)

    assert fake.requests[0]["input"] == [
        {"role": "user", "content": "Is Nairobi getting warmer?"},
        {"role": "assistant", "content": "Yes, it is."},
        {"role": "user", "content": [{"type": "input_text", "text": "And Helsinki?"}]},
    ]


async def test_current_case_is_recomputed_and_sent_before_the_question(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(text_reply("resp_1", "Hello."))

    await post_chat(chat_app(fake, cache, openai_clients), {**QUESTION, "case": HELSINKI_CASE})

    case_part, question_part = fake.requests[0]["input"][-1]["content"]
    assert case_part["type"] == "input_text"
    intro, case_json = case_part["text"].split("\n", 1)
    assert intro == CURRENT_CASE_INTRO
    assert json.loads(case_json)["results"][0]["place"]["name"] == "Helsinki"
    assert question_part == {"type": "input_text", "text": "Is Nairobi getting warmer?"}


# Tool errors


async def test_tool_error_marks_the_step_failed_and_returns_an_error_output(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    unknown = {"variable": "sea_level", "place": NAIROBI}
    fake = FakeOpenAI(
        function_call_reply("resp_1", "call_1", "analyze_trend", unknown),
        text_reply("resp_2", "That variable is not in the catalogue."),
    )

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert steps(events) == [
        ("analyze_trend", "Tested 'sea_level' in Nairobi", "started"),
        ("analyze_trend", "Tested 'sea_level' in Nairobi", "failed"),
    ]
    assert function_output(fake.requests[1]) == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "Error: 'sea_level' is not a variable in the catalogue.",
    }


async def test_input_the_model_cannot_use_returns_an_error_output(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    one_place = {"variable": "air_temp", "places": [NAIROBI]}
    fake = FakeOpenAI(
        function_call_reply("resp_1", "call_1", "compare_places", one_place),
        text_reply("resp_2", "I need two places."),
    )

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert steps(events) == [
        ("compare_places", "Compared places", "started"),
        ("compare_places", "Compared places", "failed"),
    ]
    output = function_output(fake.requests[1])["output"]
    assert output.startswith("Error: The input is not valid: places")


async def test_arguments_that_are_not_json_fail_the_step_and_the_turn_goes_on(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(
        function_call_reply("resp_1", "call_1", "find_place", '{"query": "Nair'),
        text_reply("resp_2", "Let me try that again."),
    )

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert steps(events) == [
        ("find_place", "Looked up a place", "started"),
        ("find_place", "Looked up a place", "failed"),
    ]
    assert function_output(fake.requests[1])["output"] == (
        "Error: The input is not valid: the arguments are not valid JSON"
    )
    assert names(events)[-2:] == ["check", "done"]


async def test_call_of_a_tool_never_offered_returns_an_error_output_without_a_step(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    series = {"variable": "air_temp", "place": NAIROBI}
    fake = FakeOpenAI(
        function_call_reply("resp_1", "call_1", "get_series", series),
        text_reply("resp_2", "Hello."),
    )

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert steps(events) == []
    assert function_output(fake.requests[1])["output"] == (
        "Error: There is no tool named 'get_series'."
    )


# With BrokenSource, analyze_trend fails with an error the tool layer does not expect.
BROKEN_TOOL_TURN = (
    function_call_reply(
        "resp_1", "call_1", "analyze_trend", {"variable": "air_temp", "place": NAIROBI}
    ),
    text_reply("resp_2", "The data could not be read just now."),
)


async def test_unexpected_tool_failure_returns_a_plain_error_output_and_the_turn_goes_on(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(*BROKEN_TOOL_TURN)
    app = chat_app(fake, cache, openai_clients, source=BrokenSource(RISING))

    events = await events_of(app)

    assert function_output(fake.requests[1])["output"] == f"Error: {TOOL_FAILED_MESSAGE}"
    assert [status for _, _, status in steps(events)] == ["started", "failed"]
    assert names(events)[-2:] == ["check", "done"]


async def test_unexpected_tool_failure_is_logged_by_its_error_class_only(
    cache: Cache,
    openai_clients: list[openai.AsyncOpenAI],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    fake = FakeOpenAI(*BROKEN_TOOL_TURN)
    app = chat_app(fake, cache, openai_clients, source=BrokenSource(RISING))

    await post_chat(app, QUESTION)

    assert [record for record in caplog.records if record.exc_info is not None] == []
    assert [
        record.getMessage()
        for record in caplog.records
        if record.name in {CHAT_LOGGER, OPENAI_LOGGER}
    ] == ["Tool analyze_trend failed unexpectedly with RuntimeError"]
    assert "secret" not in caplog.text


# A turn that ends without an answer (spec 8, "Failure")


async def test_refusal_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(reply("resp_1", refusal("msg_1", "I can't help with that.")))

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert events == [error_event(AI_REFUSED_MESSAGE), ("done", {})]


async def test_refusal_given_only_as_a_message_part_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    declined = refusal("msg_1", "I can't help with that.", streamed=False)
    fake = FakeOpenAI(reply("resp_1", declined))

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert events == [error_event(AI_REFUSED_MESSAGE), ("done", {})]


async def test_answer_cut_off_at_the_output_cap_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    cut_off = reply(
        "resp_1",
        message("msg_1", "Air temperature in"),
        final="response.incomplete",
        incomplete_details={"reason": "max_output_tokens"},
    )

    events = await events_of(chat_app(FakeOpenAI(cut_off), cache, openai_clients))

    assert events == [
        ("text", {"delta": "Air temperature in"}),
        error_event(AI_CUT_OFF_MESSAGE),
        ("done", {}),
    ]


async def test_response_incomplete_for_another_reason_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    filtered = reply(
        "resp_1",
        message("msg_1", "Air temperature in"),
        final="response.incomplete",
        incomplete_details={"reason": "content_filter"},
    )

    events = await events_of(chat_app(FakeOpenAI(filtered), cache, openai_clients))

    assert events[-2:] == [error_event(AI_FAILED_MESSAGE), ("done", {})]


async def test_failed_response_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    failed = reply(
        "resp_1",
        final="response.failed",
        error={"code": "server_error", "message": "The server had an error."},
    )

    events = await events_of(chat_app(FakeOpenAI(failed), cache, openai_clients))

    assert events == [error_event(AI_FAILED_MESSAGE), ("done", {})]


ERROR_EVENT_REPLY: list[Event] = [
    {"type": "response.created", "response": _response("resp_1", "in_progress", [])},
    {"type": "error", "code": "server_error", "message": "The server had an error.", "param": None},
]


async def test_error_event_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    events = await events_of(chat_app(FakeOpenAI(ERROR_EVENT_REPLY), cache, openai_clients))

    assert events == [error_event(AI_FAILED_MESSAGE), ("done", {})]


async def test_stream_cut_off_before_its_final_event_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(unfinished_reply("resp_1", "Air "))

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert events == [
        ("text", {"delta": "Air "}),
        error_event(AI_FAILED_MESSAGE),
        ("done", {}),
    ]


async def test_connection_lost_mid_answer_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(connection_lost_reply("resp_1", "Air "))

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert events == [
        ("text", {"delta": "Air "}),
        error_event(AI_FAILED_MESSAGE),
        ("done", {}),
    ]


async def test_api_error_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    events = await events_of(chat_app(FakeOpenAI(server_error()), cache, openai_clients))

    assert events == [error_event(AI_FAILED_MESSAGE), ("done", {})]


async def test_connection_lost_while_reading_an_error_reply_ends_with_an_error_then_done(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(server_error_whose_body_is_lost())

    events = await events_of(chat_app(fake, cache, openai_clients))

    assert events == [error_event(AI_FAILED_MESSAGE), ("done", {})]


async def test_iteration_limit_runs_the_last_function_calls_then_ends_with_an_error(
    cache: Cache, openai_clients: list[openai.AsyncOpenAI]
) -> None:
    fake = FakeOpenAI(*NAIROBI_TURN)

    events = await events_of(chat_app(fake, cache, openai_clients, ai_max_iterations=2))

    assert len(fake.requests) == 2
    assert names(events) == ["step", "step", "step", "step", "case", "error", "done"]
    assert events[-2] == error_event(AI_STEP_LIMIT_MESSAGE)


# The log holds no conversation text (spec 11, "Security and privacy")

SECRET_QUESTION = {"messages": [{"role": "user", "text": "Is Nairobi secretly warmer?"}]}


@pytest.mark.parametrize(
    ("ending", "logged"),
    [
        pytest.param(
            reply("resp_1", refusal("msg_1", "No secret answers.")),
            "AI turn stopped with refusal",
            id="refusal",
        ),
        pytest.param(
            reply(
                "resp_1",
                message("msg_1", "A secret answer"),
                final="response.incomplete",
                incomplete_details={"reason": "max_output_tokens"},
            ),
            "AI turn stopped with max_output_tokens",
            id="cut-off",
        ),
        pytest.param(
            reply(
                "resp_1",
                final="response.failed",
                error={"code": "server_error", "message": "secret"},
            ),
            "AI turn stopped with failed",
            id="failed",
        ),
        pytest.param(ERROR_EVENT_REPLY, "AI turn stopped with error", id="error-event"),
        pytest.param(
            unfinished_reply("resp_1", "A secret answer"),
            "AI turn stopped with no final event",
            id="no-final-event",
        ),
        pytest.param(
            connection_lost_reply("resp_1", "A secret answer"),
            "AI call failed with APITimeoutError",
            id="connection-lost",
        ),
        pytest.param(
            server_error_whose_body_is_lost(),
            "AI call failed with ReadTimeout",
            id="error-body-lost",
        ),
    ],
)
async def test_turn_that_ends_without_an_answer_logs_how_it_ended_and_no_conversation_text(
    cache: Cache,
    openai_clients: list[openai.AsyncOpenAI],
    caplog: pytest.LogCaptureFixture,
    ending: Reply,
    logged: str,
) -> None:
    caplog.set_level(logging.INFO)
    fake = FakeOpenAI(
        function_call_reply("resp_0", "call_0", "find_place", {"query": "Nairobi"}), ending
    )

    await post_chat(chat_app(fake, cache, openai_clients), SECRET_QUESTION)

    assert [
        (record.getMessage(), record.exc_info)
        for record in caplog.records
        if record.name in {CHAT_LOGGER, OPENAI_LOGGER}
    ] == [(logged, None)]
    assert "secret" not in caplog.text.lower()
