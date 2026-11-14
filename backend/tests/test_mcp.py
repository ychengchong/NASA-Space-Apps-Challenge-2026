"""The MCP adapter (spec 9): the tools through the SDK's in-process client, and /mcp over HTTP."""

import base64
import json
import logging
import re
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

import anyio
import httpx
import httpx2
import pytest
from fastapi import FastAPI
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, ImageContent, TextContent
from starlette.types import Message, Scope

from app.adapters.mcp_server import CASE_LINK_TEXT, MAP_LINK_TEXT, MCP_PATH, create_mcp_server
from app.cache import Cache
from app.errors import UnknownVariableError
from app.main import create_app
from app.models import (
    AnalyzeTrendInput,
    ComparePlacesInput,
    FindPlaceInput,
    GetSeriesInput,
    Investigation,
    MapTrendsInput,
    SearchVariablesInput,
    TrendMap,
)
from app.render import render_case_png
from app.services import Services
from app.tools.places import find_place
from app.tools.series import get_series
from app.tools.trends import analyze_trend, compare_places, map_trends
from app.tools.variables import search_variables
from tests.app_client import BASE_URL, make_services, write_web_app
from tests.fake_source import FakeSource, RegionalFakeSource, line, monthly_from_yearly

pytestmark = pytest.mark.anyio

RISING = monthly_from_yearly(line(0.05))
HELSINKI = {"lat": 60.17, "lon": 24.94, "name": "Helsinki"}
NAIROBI = {"lat": -1.29, "lon": 36.82, "name": "Nairobi"}
HELSINKI_CASE: dict[str, Any] = {"variable": "air_temp", "place": HELSINKI}
BOX = {"south": 55.0, "west": 20.0, "north": 65.0, "east": 30.0}

TOOL_NAMES = {
    "search_variables",
    "find_place",
    "analyze_trend",
    "compare_places",
    "get_series",
    "map_trends",
    "get_chart",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LOCAL_URL = "http://localhost:8000"
FOREIGN_HOST = "evil.example"
FOREIGN_ORIGIN = "https://evil.example"
# Streamable HTTP (spec 9): a client accepts both a JSON answer and an event stream.
MCP_HEADERS = {"Accept": "application/json, text/event-stream"}
LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
# The MCP revision of 28 July 2026 (spec 9), which names the method in a header and the
# protocol version and client capabilities in each request's _meta.
MODERN_PROTOCOL_VERSION = "2026-07-28"
MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
}
JSON_RPC_METHOD_NOT_FOUND = -32601
# A listen stream sends its first ping after 15 s; an answer must come long before that.
ANSWER_TIMEOUT_SECONDS = 5
# Every standard HTTP method but POST, the one method /mcp takes (spec 9).
REFUSED_MCP_METHODS = ["GET", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]

INVALID_ARGUMENTS = [
    ("analyze_trend", {"variable": "air_temp", "place": {"lat": 100.0, "lon": 24.94}}),
    ("analyze_trend", {"variable": "air_temp", "place": HELSINKI, "season": "winter"}),
    ("analyze_trend", {"place": HELSINKI}),
    ("compare_places", {"variable": "air_temp", "places": [HELSINKI]}),
    ("find_place", {"query": ""}),
    ("map_trends", {"variable": "air_temp", "box": {**BOX, "north": 95.0}}),
]
INVALID_INPUT_PREFIX = "The input is not valid:"
# Pydantic's error text: the argument model's name, the rejected value and its documentation link.
VALIDATOR_INTERNALS = ("Arguments", "input_value", "input_type", "errors.pydantic.dev")


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[Cache]:
    cache = Cache(tmp_path / "cache.sqlite")
    yield cache
    cache.close()


@pytest.fixture
def services(cache: Cache) -> Services:
    return make_services(cache, FakeSource(RISING))


@pytest.fixture
def web_dir(tmp_path: Path) -> Path:
    return write_web_app(tmp_path / "dist")


@asynccontextmanager
async def mcp_client(services: Services) -> AsyncIterator[Client]:
    """The SDK's client, connected in-process to a server on `services`."""
    async with Client(create_mcp_server(lambda: services)) as client:
        yield client


async def call(services: Services, tool: str, arguments: Mapping[str, Any]) -> CallToolResult:
    async with mcp_client(services) as client:
        return await client.call_tool(tool, dict(arguments))


def texts(result: CallToolResult) -> list[str]:
    return [block.text for block in result.content if isinstance(block, TextContent)]


def png_bytes(result: CallToolResult) -> bytes:
    (block,) = result.content
    assert isinstance(block, ImageContent)
    assert block.mime_type == "image/png"
    return base64.b64decode(block.data)


# Listing the tools


async def test_lists_the_seven_tools(services: Services) -> None:
    async with mcp_client(services) as client:
        listed = await client.list_tools()

    assert {tool.name for tool in listed.tools} == TOOL_NAMES


async def test_every_tool_has_a_description_and_is_marked_read_only(services: Services) -> None:
    async with mcp_client(services) as client:
        listed = await client.list_tools()

    for tool in listed.tools:
        assert tool.description
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.idempotent_hint is True


@pytest.mark.parametrize(
    ("tool_name", "field"), [("search_variables", "region_types"), ("find_place", "region_type")]
)
async def test_tool_description_names_the_region_field_its_results_carry(
    services: Services, tool_name: str, field: str
) -> None:
    async with mcp_client(services) as client:
        listed = await client.list_tools()

    (tool,) = [tool for tool in listed.tools if tool.name == tool_name]
    assert tool.description is not None
    assert re.search(rf"\b{field}\b", tool.description)


async def test_find_place_description_says_a_megacity_carries_a_region_type(
    services: Services,
) -> None:
    async with mcp_client(services) as client:
        listed = await client.list_tools()

    (tool,) = [tool for tool in listed.tools if tool.name == "find_place"]
    assert tool.description is not None
    assert re.search(r"\bmegacity\b", tool.description)


async def test_input_schema_is_the_models_with_from_as_its_key(services: Services) -> None:
    async with mcp_client(services) as client:
        listed = await client.list_tools()

    (tool,) = [tool for tool in listed.tools if tool.name == "analyze_trend"]
    schema = tool.input_schema
    assert set(schema["properties"]) == {"variable", "place", "from", "to", "season", "scan"}
    assert set(schema["required"]) == {"variable", "place"}
    assert schema["properties"]["season"]["enum"] == ["annual", "DJF", "MAM", "JJA", "SON"]


async def test_tools_with_data_have_an_output_schema_and_get_chart_has_none(
    services: Services,
) -> None:
    async with mcp_client(services) as client:
        listed = await client.list_tools()

    schemas = {tool.name: tool.output_schema for tool in listed.tools}
    assert schemas.pop("get_chart") is None
    assert all(schema is not None for schema in schemas.values())
    assert "from" in json.dumps(schemas["analyze_trend"])


# Analysis tools


async def test_analyze_trend_returns_the_investigation_as_structured_data(
    services: Services,
) -> None:
    expected = await analyze_trend(
        AnalyzeTrendInput.model_validate(HELSINKI_CASE), services.tool_context()
    )

    result = await call(services, "analyze_trend", HELSINKI_CASE)

    assert result.is_error is False
    assert result.structured_content == expected.model_dump(mode="json")


async def test_analyze_trend_text_block_holds_the_verdict_sentence_and_case_link(
    services: Services,
) -> None:
    result = await call(services, "analyze_trend", HELSINKI_CASE)

    investigation = Investigation.model_validate(result.structured_content)
    assert investigation.app_url.startswith(f"{BASE_URL}/case?")
    assert texts(result)[0] == (
        f"{investigation.results[0].verdict.sentence}\n\n"
        f"{CASE_LINK_TEXT.format(url=investigation.app_url)}"
    )


async def test_structured_result_is_repeated_as_json_in_the_last_text_block(
    services: Services,
) -> None:
    result = await call(services, "analyze_trend", HELSINKI_CASE)

    assert json.loads(texts(result)[-1]) == result.structured_content


async def test_analyze_trend_reads_the_first_year_from_the_key_from(services: Services) -> None:
    result = await call(services, "analyze_trend", {**HELSINKI_CASE, "from": 2000})

    assert result.structured_content is not None
    assert result.structured_content["requested"]["from"] == 2000


async def test_compare_places_text_block_holds_the_summary(services: Services) -> None:
    arguments = {"variable": "air_temp", "places": [HELSINKI, NAIROBI]}
    expected = await compare_places(
        ComparePlacesInput.model_validate(arguments), services.tool_context()
    )

    result = await call(services, "compare_places", arguments)

    assert result.structured_content == expected.model_dump(mode="json")
    assert expected.summary is not None
    assert texts(result)[0] == (
        f"{expected.summary}\n\n{CASE_LINK_TEXT.format(url=expected.app_url)}"
    )


async def test_map_trends_text_block_holds_the_area_mean_sentence_and_map_link(
    cache: Cache,
) -> None:
    services = make_services(cache, RegionalFakeSource({(60.0, 25.0): RISING}))
    arguments = {"variable": "air_temp", "box": BOX}
    expected = await map_trends(MapTrendsInput.model_validate(arguments), services.tool_context())

    result = await call(services, "map_trends", arguments)

    assert TrendMap.model_validate(result.structured_content) == expected
    assert texts(result)[0] == (
        f"{expected.area_mean.verdict.sentence}\n\n{MAP_LINK_TEXT.format(url=expected.app_url)}"
    )


# Data tools


async def test_search_variables_lists_its_matches_under_result(services: Services) -> None:
    expected = search_variables(SearchVariablesInput(query="rain"))

    result = await call(services, "search_variables", {"query": "rain"})

    assert result.structured_content == {
        "result": [variable.model_dump(mode="json") for variable in expected]
    }


async def test_find_place_lists_its_candidates_under_result(services: Services) -> None:
    expected = find_place(FindPlaceInput(query="Helsinki"))

    result = await call(services, "find_place", {"query": "Helsinki"})

    assert expected
    assert result.structured_content == {
        "result": [candidate.model_dump(mode="json") for candidate in expected]
    }


async def test_get_series_returns_the_series(services: Services) -> None:
    arguments = {**HELSINKI_CASE, "resolution": "yearly", "from": 2001, "to": 2010}
    expected = await get_series(GetSeriesInput.model_validate(arguments), services.tool_context())

    result = await call(services, "get_series", arguments)

    assert result.structured_content == expected.model_dump(mode="json")
    assert len(texts(result)) == 1


# get_chart


async def test_get_chart_for_one_place_returns_the_case_png(services: Services) -> None:
    investigation = await analyze_trend(
        AnalyzeTrendInput.model_validate(HELSINKI_CASE), services.tool_context()
    )

    result = await call(services, "get_chart", {"variable": "air_temp", "places": [HELSINKI]})

    assert result.is_error is False
    assert result.structured_content is None
    png = png_bytes(result)
    assert png.startswith(PNG_SIGNATURE)
    assert png == render_case_png(investigation)


async def test_get_chart_for_two_places_draws_the_comparison(services: Services) -> None:
    arguments = {"variable": "air_temp", "places": [HELSINKI, NAIROBI], "from": 1991}
    investigation = await compare_places(
        ComparePlacesInput.model_validate(arguments), services.tool_context()
    )

    result = await call(services, "get_chart", arguments)

    assert png_bytes(result) == render_case_png(investigation)


@pytest.mark.parametrize("place_count", [0, 5])
async def test_get_chart_takes_one_to_four_places(services: Services, place_count: int) -> None:
    arguments = {"variable": "air_temp", "places": [HELSINKI] * place_count}

    result = await call(services, "get_chart", arguments)

    assert result.is_error is True


# Errors


async def test_app_error_becomes_a_tool_error_with_its_plain_message(services: Services) -> None:
    arguments = {"variable": "no_such_variable", "place": HELSINKI}
    with pytest.raises(UnknownVariableError) as raised:
        await analyze_trend(AnalyzeTrendInput.model_validate(arguments), services.tool_context())

    result = await call(services, "analyze_trend", arguments)

    assert result.is_error is True
    assert texts(result) == [raised.value.message]


@pytest.mark.parametrize(("tool", "arguments"), INVALID_ARGUMENTS)
async def test_invalid_input_returns_a_tool_error(
    services: Services, tool: str, arguments: dict[str, Any]
) -> None:
    result = await call(services, tool, arguments)

    assert result.is_error is True
    assert result.structured_content is None


@pytest.mark.parametrize(("tool", "arguments"), INVALID_ARGUMENTS)
async def test_invalid_input_message_holds_no_validator_internals(
    services: Services, tool: str, arguments: dict[str, Any]
) -> None:
    result = await call(services, tool, arguments)

    (message,) = texts(result)
    assert message.startswith(INVALID_INPUT_PREFIX)
    assert not any(internal in message for internal in VALIDATOR_INTERNALS)


async def test_invalid_input_message_names_the_field_and_the_rule(services: Services) -> None:
    arguments = {"variable": "air_temp", "place": {"lat": 100.0, "lon": 24.94}}

    result = await call(services, "analyze_trend", arguments)

    assert texts(result) == [
        f"{INVALID_INPUT_PREFIX} place.lat: Input should be less than or equal to 90"
    ]


async def test_building_the_server_leaves_the_root_logger_alone(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "level", logging.WARNING)

    create_mcp_server(lambda: services)

    assert root.handlers == []
    assert root.level == logging.WARNING


# /mcp over HTTP


@asynccontextmanager
async def http_client(app: FastAPI, base_url: str = LOCAL_URL) -> AsyncIterator[httpx.AsyncClient]:
    """An HTTP client for `app`, which runs its lifespan, as a server would, while it is open."""
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=base_url) as client,
    ):
        yield client


async def post_mcp(
    app: FastAPI, base_url: str = LOCAL_URL, headers: Mapping[str, str] | None = None
) -> httpx.Response:
    async with http_client(app, base_url) as client:
        return await client.post(
            MCP_PATH, json=LIST_TOOLS, headers={**MCP_HEADERS, **(headers or {})}
        )


async def test_post_mcp_answers_at_mcp_itself_beside_the_web_app(
    services: Services, web_dir: Path
) -> None:
    response = await post_mcp(create_app(services, static_dir=web_dir))

    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert names == TOOL_NAMES


@pytest.mark.parametrize("with_web_app", [True, False])
async def test_get_mcp_answers_405_rather_than_opening_an_event_stream(
    services: Services, tmp_path: Path, with_web_app: bool
) -> None:
    static_dir = write_web_app(tmp_path / "dist") if with_web_app else tmp_path / "missing"
    app = create_app(services, static_dir=static_dir)

    async with http_client(app) as client:
        response = await client.get(MCP_PATH, headers=MCP_HEADERS)

    assert response.status_code == 405
    assert response.headers["Allow"] == "POST"
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.parametrize("method", REFUSED_MCP_METHODS)
async def test_every_method_but_post_on_mcp_answers_405_in_the_error_shape(
    services: Services, web_dir: Path, method: str
) -> None:
    async with http_client(create_app(services, static_dir=web_dir)) as client:
        response = await client.request(method, MCP_PATH, headers=MCP_HEADERS)

    assert response.status_code == 405
    assert response.headers["Allow"] == "POST"
    assert response.json()["error"]["code"] == "bad_request"


async def test_head_on_mcp_answers_405_allowing_post(services: Services, web_dir: Path) -> None:
    async with http_client(create_app(services, static_dir=web_dir)) as client:
        response = await client.head(MCP_PATH, headers=MCP_HEADERS)

    assert response.status_code == 405
    assert response.headers["Allow"] == "POST"


async def post_modern(app: FastAPI, method: str, params: Mapping[str, Any]) -> httpx.Response:
    """POST one request of the 2026-07-28 revision to /mcp; fails if no answer comes in time."""
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {"_meta": MODERN_META, **params}}
    headers = {**MCP_HEADERS, "MCP-Protocol-Version": MODERN_PROTOCOL_VERSION, "Mcp-Method": method}
    async with http_client(app) as client:
        with anyio.fail_after(ANSWER_TIMEOUT_SECONDS):
            return await client.post(MCP_PATH, json=body, headers=headers)


async def test_subscriptions_listen_gets_a_json_error_rather_than_an_event_stream(
    services: Services, web_dir: Path
) -> None:
    response = await post_modern(
        create_app(services, static_dir=web_dir),
        "subscriptions/listen",
        {"notifications": {"toolsListChanged": True}},
    )

    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"]["code"] == JSON_RPC_METHOD_NOT_FOUND


async def test_discover_advertises_no_list_changes_or_subscriptions(
    services: Services, web_dir: Path
) -> None:
    response = await post_modern(create_app(services, static_dir=web_dir), "server/discover", {})

    capabilities = response.json()["result"]["capabilities"]
    assert not capabilities["tools"].get("listChanged")
    assert not capabilities.get("resources", {}).get("subscribe")


async def test_mcp_refuses_a_host_that_is_not_allowed(services: Services, web_dir: Path) -> None:
    response = await post_mcp(
        create_app(services, static_dir=web_dir), headers={"Host": FOREIGN_HOST}
    )

    assert response.status_code == 421


async def test_a_refused_host_or_origin_is_not_logged(
    services: Services, web_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    async with http_client(create_app(services, static_dir=web_dir)) as client:
        for header in ({"Host": FOREIGN_HOST}, {"Origin": FOREIGN_ORIGIN}):
            await client.post(MCP_PATH, json=LIST_TOOLS, headers={**MCP_HEADERS, **header})

    assert FOREIGN_HOST not in caplog.text


async def test_mcp_refuses_an_origin_that_is_not_allowed(services: Services, web_dir: Path) -> None:
    response = await post_mcp(
        create_app(services, static_dir=web_dir), headers={"Origin": FOREIGN_ORIGIN}
    )

    assert response.status_code == 403


async def test_mcp_accepts_the_host_and_origin_of_the_public_base_url(
    services: Services, web_dir: Path
) -> None:
    response = await post_mcp(
        create_app(services, static_dir=web_dir), base_url=BASE_URL, headers={"Origin": BASE_URL}
    )

    assert response.status_code == 200


async def test_mcp_refuses_the_public_host_when_no_public_base_url_is_set(
    services: Services, web_dir: Path
) -> None:
    local_only = replace(services, settings=replace(services.settings, public_base_url=None))

    response = await post_mcp(create_app(local_only, static_dir=web_dir), base_url=BASE_URL)

    assert response.status_code == 421


async def test_mcp_requests_count_toward_the_rate_limit(cache: Cache, web_dir: Path) -> None:
    app = create_app(
        make_services(cache, FakeSource(RISING), rate_limit_per_minute=1), static_dir=web_dir
    )

    async with http_client(app) as client:
        first = await client.post(MCP_PATH, json=LIST_TOOLS, headers=MCP_HEADERS)
        second = await client.post(MCP_PATH, json=LIST_TOOLS, headers=MCP_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"


async def test_sdk_client_completes_an_investigation_over_http(
    services: Services, web_dir: Path
) -> None:
    app = create_app(services, static_dir=web_dir)
    transport = httpx2.ASGITransport(app=app)

    async with (
        app.router.lifespan_context(app),
        httpx2.AsyncClient(transport=transport, base_url=LOCAL_URL) as http,
        Client(streamable_http_client(f"{LOCAL_URL}{MCP_PATH}", http_client=http)) as client,
    ):
        result = await client.call_tool("analyze_trend", HELSINKI_CASE)

    investigation = Investigation.model_validate(result.structured_content)
    assert investigation.results[0].verdict.sentence in texts(result)[0]


# The request log's logger, and the status it gives a request whose client left before the answer.
REQUEST_LOGGER = "app.main"
CLIENT_CLOSED_REQUEST = 499


async def post_mcp_from_a_client_that_disconnects(
    services: Services, web_dir: Path
) -> list[Message]:
    """POST /mcp from a client that leaves after sending half of its body.

    Returns the messages the app sent back.
    """
    body = json.dumps(LIST_TOOLS).encode()
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "server": ("localhost", 8000),
        "client": ("192.0.2.1", 50000),
        "root_path": "",
        "path": MCP_PATH,
        "raw_path": MCP_PATH.encode(),
        "query_string": b"",
        "headers": [
            (b"host", b"localhost:8000"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            *((name.lower().encode(), value.encode()) for name, value in MCP_HEADERS.items()),
        ],
    }
    arriving: list[Message] = [
        {"type": "http.request", "body": body[: len(body) // 2], "more_body": True},
        {"type": "http.disconnect"},
    ]
    sent: list[Message] = []

    async def receive() -> Message:
        return arriving.pop(0) if len(arriving) > 1 else arriving[0]

    async def send(message: Message) -> None:
        sent.append(message)

    app = create_app(services, static_dir=web_dir)
    async with app.router.lifespan_context(app):
        await app(scope, receive, send)
    return sent


async def test_client_that_disconnects_mid_request_to_mcp_is_not_logged_as_an_error(
    services: Services, web_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    await post_mcp_from_a_client_that_disconnects(services, web_dir)

    assert [record for record in caplog.records if record.levelno >= logging.ERROR] == []


async def test_client_that_disconnects_mid_request_to_mcp_gets_no_answer(
    services: Services, web_dir: Path
) -> None:
    assert await post_mcp_from_a_client_that_disconnects(services, web_dir) == []


async def test_request_log_records_a_client_that_disconnects_mid_request_to_mcp_as_closed(
    services: Services, web_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    await post_mcp_from_a_client_that_disconnects(services, web_dir)

    messages = [record.getMessage() for record in caplog.records if record.name == REQUEST_LOGGER]
    assert len(messages) == 1
    assert re.fullmatch(rf"POST {MCP_PATH} {CLIENT_CLOSED_REQUEST} \d+ ms", messages[0])
