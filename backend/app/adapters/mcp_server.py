"""The MCP adapter of spec 9: the six tools of the tool layer, plus get_chart, at POST /mcp.

Translation only, no analysis. Each tool validates its input with the Pydantic model of spec 5,
calls the same tool function as the REST adapter and returns the result as structured data. The
analysis tools add a text block with the app's fixed sentence and the link to the case, and
get_chart returns the case's chart as a PNG image block.
"""

import inspect
import json
import logging
from collections.abc import Awaitable, Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from typing import Annotated, Any, NoReturn
from urllib.parse import urlsplit

import anyio.to_thread
from mcp.server import MCPServer
from mcp.server.mcpserver import Context, Image
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import (
    CallToolResult,
    ContentBlock,
    InputRequiredResult,
    TextContent,
    ToolAnnotations,
)
from pydantic import Field, ValidationError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import ClientDisconnect, Request
from starlette.routing import Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import AppError, first_problem
from app.models import (
    MAX_COMPARE_PLACES,
    MIN_COMPARE_PLACES,
    PLACE_NAME_MAX_LENGTH,
    AnalyzeTrendInput,
    ComparePlacesInput,
    FindPlaceInput,
    GetSeriesInput,
    Investigation,
    MapTrendsInput,
    Model,
    PeriodInput,
    PlaceCandidate,
    PlaceInput,
    SearchVariablesInput,
    Series,
    TrendMap,
    VariableSummary,
)
from app.render import render_case_png
from app.services import Services
from app.stats import MIN_YEARS_FOR_TEST
from app.tools.context import ToolContext
from app.tools.places import MAX_PLACE_CANDIDATES, find_place
from app.tools.series import get_series
from app.tools.trends import (
    MAX_BOX_SIDE_DEGREES,
    MIN_BOX_SIDE_DEGREES,
    analyze_trend,
    compare_places,
    map_trends,
)
from app.tools.variables import search_variables

# Spec 10: the MCP endpoint.
MCP_PATH = "/mcp"
SERVER_NAME = "trend-detective"
SERVER_TITLE = "Trend Detective"
SERVER_INSTRUCTIONS = (
    "Trend Detective tests whether a climate variable has risen or fallen over the years at a "
    "place, using NASA POWER monthly data from 1981 onward. Use find_place to turn a place name "
    "into coordinates and search_variables when you are unsure of a variable id. Then call "
    "analyze_trend for one place, compare_places for several, or map_trends for an area. Each "
    "verdict sentence and summary is fixed text from the app: quote it as given and do not "
    "recompute its numbers. Pass on any cautions. Call get_chart only when a picture would help."
)

# Spec 9: structuredContent is a JSON object, so a list result travels under this key, the
# key the SDK itself uses to wrap a list in the tool's output schema.
LIST_RESULT_KEY = "result"
CASE_LINK_TEXT = "Open this case in Trend Detective: {url}"
MAP_LINK_TEXT = "Open this map in Trend Detective: {url}"
PNG_FORMAT = "png"
# Spec 9: tool arguments that do not validate get a plain message, worded as chat's (spec 8).
INVALID_INPUT_TEXT = "The input is not valid: {problem}"

# Spec 5: every tool is read-only, and the same inputs always give the same output.
READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True)

# Spec 9, "Implementation": without an allowlist the SDK answers only on localhost and returns
# 421 elsewhere. These loopback names are always allowed, as in the SDK's own default.
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "[::1]")
LOOPBACK_SCHEME = "http"
ANY_PORT = ":*"
# The methods /mcp answers without sessions: a client sends each message with POST.
MCP_ALLOWED_METHODS = "POST"
# Spec 9: every other standard method gets 405, before it reaches the SDK's route.
MCP_REFUSED_METHODS = ("GET", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE")


class GetChartInput(PeriodInput):
    """Spec 9: the input of compare_places, but from one place up to MAX_COMPARE_PLACES.

    The period scan is left out, because the chart does not draw it.
    """

    variable: str = Field(description="A catalogue variable id, such as 'air_temp'.")
    places: list[PlaceInput] = Field(min_length=1, max_length=MAX_COMPARE_PLACES)


# Tool descriptions, written for the calling model (spec 9, "Implementation")

_PERIOD_TEXT = (
    "Leave out from and to to use the variable's whole record up to the last complete year; "
    "unsupported years are rejected for user confirmation. season picks months "
    "day-weighted into each "
    "year's value."
)
_INVESTIGATION_TEXT = (
    "In each result, series holds the yearly values in the variable's units, null where a year "
    "is missing. In trend, sen_slope, sen_ci95 and ols_slope are in the variable's rate_units "
    "per decade, total_change and line are in its units. Unsupported intervals and "
    "OLS tests are null. "
    "mk_p is available only for validated complete annual T2M cases with 20-45 years. "
    "verdict.kind includes inference_unavailable; inference_reason explains why. "
    "A zero median rate does not override valid rank evidence. verdict.sentence is canonical, and "
    "verdict.cautions lists the cautions to pass on, most important first. app_url opens the "
    "case in the Trend Detective web app."
)

SEARCH_VARIABLES_DESCRIPTION = (
    "Search the catalogue of climate variables with plain words, such as 'rain' or 'hotter'. "
    "Use it when you are not sure which variable id fits a question. An empty query lists every "
    "variable; theme keeps one theme: temperature, water, wind or sunlight. Returns the matching "
    "variables under result, best match first, each with its id, name, definition, units, "
    "rate_units (the units before 'per decade'), record_start (the first year of data), the ids "
    "of related variables, region_types (the region types where a trend in the variable is "
    "worth testing), and any standing trend_note to pass on."
)
FIND_PLACE_DESCRIPTION = (
    "Find a city or region by name, ignoring case and accents. Use it whenever the user names a "
    f"place, before the tools that take coordinates. Returns up to {MAX_PLACE_CANDIDATES} "
    "candidates under result, best match first, each with name, country, lat and lon in "
    "degrees, kind (city or region) and region_type: the type of a region, such as desert, or "
    "megacity for a city of 10 million or more; null for other cities. Pass the chosen "
    "candidate's lat, lon and name on unchanged."
)
ANALYZE_TREND_DESCRIPTION = (
    "Test whether one variable has a trend at one place, with the Mann-Kendall test and Sen's "
    "slope on yearly values. Use it for questions such as 'Is Nairobi getting warmer?'. The "
    "data come from the grid cell that contains the point. place.name is a display name of "
    f"{PLACE_NAME_MAX_LENGTH} characters at most. {_PERIOD_TEXT} Set scan to true to also get "
    "trend.scan: descriptive Sen rates with null p-values for each start year that leaves at "
    f"least {MIN_YEARS_FOR_TEST} years. Returns an Investigation with requested (the years and "
    f"season used) and one result. {_INVESTIGATION_TEXT} A text block repeats the verdict "
    "sentence and the link."
)
COMPARE_PLACES_DESCRIPTION = (
    f"Test the same variable at {MIN_COMPARE_PLACES} to {MAX_COMPARE_PLACES} places over the "
    "identical common complete years. This is descriptive, not a test of differences "
    "between places. "
    "Use it when the user names two or more places. The period and scan work as in "
    "analyze_trend. Returns one Investigation with one result per place, in the order given, "
    "plus contrast (opposite_directions, same_direction or unclear) and summary, the app's fixed "
    f"comparison sentence. {_INVESTIGATION_TEXT} A text block repeats the summary and the link."
)
GET_SERIES_DESCRIPTION = (
    "Return the raw values of one variable at one place, monthly or yearly. Use it only when "
    "the user wants the values themselves, for a table or their own analysis: analyze_trend "
    f"already includes the yearly values. {_PERIOD_TEXT} Returns a Series with the variable, "
    "the place with the grid cell used, the resolution, and values, each with a date "
    "('YYYY-MM' or 'YYYY') and a value in the variable's units, null when missing."
)
MAP_TRENDS_DESCRIPTION = (
    "Map the trend of one variable across a box of latitude and longitude. Use it only when the "
    "user asks about an area or a pattern, not a single place. box gives south, west, north and "
    f"east in degrees; each side must be from {MIN_BOX_SIDE_DEGREES:g} to "
    f"{MAX_BOX_SIDE_DEGREES:g} degrees, with south below north and west below east, so a box "
    "cannot cross the 180 degree meridian. The period works as in analyze_trend. Returns a "
    "TrendMap: sen_slope is descriptive, mk_p is null and significant is false for every cell. "
    "The fixed-footprint latitude-weighted area_mean is descriptive too. This is a latest-data "
    "view; its URL does not freeze a regional snapshot. app_url opens it in the app. "
    "A text block repeats the "
    "area mean's verdict sentence and the link."
)
GET_CHART_DESCRIPTION = (
    "Draw a PNG chart of a case: each place's yearly values and trend line, the verdict "
    "sentence or the comparison summary, and the data source. It takes the input of "
    f"compare_places, but with 1 to {MAX_COMPARE_PLACES} places and no scan. "
    "Call it only when a picture would help the user, because an image costs many tokens. "
    "Returns one PNG image."
)


# What each tool does with its validated input


async def _search_variables(inp: SearchVariablesInput, ctx: ToolContext) -> CallToolResult:
    return _list_result(search_variables(inp))


async def _find_place(inp: FindPlaceInput, ctx: ToolContext) -> CallToolResult:
    return _list_result(find_place(inp))


async def _analyze_trend(inp: AnalyzeTrendInput, ctx: ToolContext) -> CallToolResult:
    return _case_result(await analyze_trend(inp, ctx))


async def _compare_places(inp: ComparePlacesInput, ctx: ToolContext) -> CallToolResult:
    return _case_result(await compare_places(inp, ctx))


async def _get_series(inp: GetSeriesInput, ctx: ToolContext) -> CallToolResult:
    return _data_result(await get_series(inp, ctx))


async def _map_trends(inp: MapTrendsInput, ctx: ToolContext) -> CallToolResult:
    trend_map = await map_trends(inp, ctx)
    text = _with_link(trend_map.area_mean.verdict.sentence, MAP_LINK_TEXT, trend_map.app_url)
    return _data_result(trend_map, text)


async def _get_chart(inp: GetChartInput, ctx: ToolContext) -> CallToolResult:
    investigation = await _chart_case(inp, ctx)
    # Drawing is CPU work that would hold up every other request, so it runs in a worker thread.
    png = await anyio.to_thread.run_sync(render_case_png, investigation)
    return CallToolResult(content=[Image(data=png, format=PNG_FORMAT).to_image_content()])


async def _chart_case(inp: GetChartInput, ctx: ToolContext) -> Investigation:
    """The case the chart shows: analyze_trend for one place, compare_places for more."""
    fields = inp.model_dump()
    if len(inp.places) == 1:
        place = fields.pop("places")[0]
        return await analyze_trend(
            AnalyzeTrendInput.model_validate({**fields, "place": place}), ctx
        )
    return await compare_places(ComparePlacesInput.model_validate(fields), ctx)


# Results


def _case_result(investigation: Investigation) -> CallToolResult:
    """The Investigation as data, after a text block with its headline and link (spec 9)."""
    headline = investigation.summary or " ".join(
        result.verdict.sentence for result in investigation.results
    )
    return _data_result(investigation, _with_link(headline, CASE_LINK_TEXT, investigation.app_url))


def _with_link(sentence: str, link_text: str, url: str) -> str:
    return f"{sentence}\n\n{link_text.format(url=url)}"


def _data_result(data: Model, text: str | None = None) -> CallToolResult:
    return _structured_result(data.model_dump(mode="json"), text)


def _list_result(items: Sequence[Model]) -> CallToolResult:
    return _structured_result({LIST_RESULT_KEY: [item.model_dump(mode="json") for item in items]})


def _structured_result(structured: dict[str, Any], text: str | None = None) -> CallToolResult:
    # Spec 9: the JSON is repeated in a text block for clients that do not read structuredContent.
    content: list[ContentBlock] = [] if text is None else [TextContent(type="text", text=text)]
    content.append(TextContent(type="text", text=json.dumps(structured, ensure_ascii=False)))
    return CallToolResult(content=content, structured_content=structured)


def _error_result(message: str) -> CallToolResult:
    """A tool error carrying the error's plain message, as the REST error shape does."""
    return CallToolResult(content=[TextContent(type="text", text=message)], is_error=True)


# The server


class _PlainErrorServer(MCPServer):
    """An MCPServer that answers tool arguments that do not validate with a plain message.

    The SDK validates the arguments before the tool runs. Its own error text is pydantic's: the
    argument model's name, the rejected values and a documentation link, internals that REST
    also replaces with a plain message (spec 10).
    """

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context[Any, Any] | None = None
    ) -> CallToolResult | InputRequiredResult:
        try:
            return await super().call_tool(name, arguments, context)
        except ToolError as error:
            # An UnexpectedToolError is a crash, whose text the SDK already withholds.
            invalid = error.__cause__
            if isinstance(error, UnexpectedToolError) or not isinstance(invalid, ValidationError):
                raise
            return _error_result(INVALID_INPUT_TEXT.format(problem=first_problem(invalid)))


@dataclass(frozen=True)
class _ToolSpec[InputT: Model]:
    name: str
    description: str
    input_model: type[InputT]
    # The type of the structured result, which gives the tool's output schema; None for get_chart,
    # whose result is an image only.
    output: object | None
    run: Callable[[InputT, ToolContext], Awaitable[CallToolResult]]


TOOL_SPECS: tuple[_ToolSpec[Any], ...] = (
    _ToolSpec(
        name="search_variables",
        description=SEARCH_VARIABLES_DESCRIPTION,
        input_model=SearchVariablesInput,
        output=list[VariableSummary],
        run=_search_variables,
    ),
    _ToolSpec(
        name="find_place",
        description=FIND_PLACE_DESCRIPTION,
        input_model=FindPlaceInput,
        output=list[PlaceCandidate],
        run=_find_place,
    ),
    _ToolSpec(
        name="analyze_trend",
        description=ANALYZE_TREND_DESCRIPTION,
        input_model=AnalyzeTrendInput,
        output=Investigation,
        run=_analyze_trend,
    ),
    _ToolSpec(
        name="compare_places",
        description=COMPARE_PLACES_DESCRIPTION,
        input_model=ComparePlacesInput,
        output=Investigation,
        run=_compare_places,
    ),
    _ToolSpec(
        name="get_series",
        description=GET_SERIES_DESCRIPTION,
        input_model=GetSeriesInput,
        output=Series,
        run=_get_series,
    ),
    _ToolSpec(
        name="map_trends",
        description=MAP_TRENDS_DESCRIPTION,
        input_model=MapTrendsInput,
        output=TrendMap,
        run=_map_trends,
    ),
    _ToolSpec(
        name="get_chart",
        description=GET_CHART_DESCRIPTION,
        input_model=GetChartInput,
        output=None,
        run=_get_chart,
    ),
)


def create_mcp_server(get_services: Callable[[], Services]) -> MCPServer:
    """An MCP server with the seven tools of spec 9, each running on `get_services()`.

    `get_services` is called once per tool call, so the services may be built after the server.
    Subscriptions are off: the server never sends a change notification, and without them
    `subscriptions/listen` is not served, so it cannot hold an event stream open (spec 9).
    """
    with _root_logger_kept():
        server: MCPServer = _PlainErrorServer(
            SERVER_NAME,
            title=SERVER_TITLE,
            instructions=SERVER_INSTRUCTIONS,
            subscriptions=False,
        )
    for spec in TOOL_SPECS:
        _add_tool(server, spec, get_services)
    return server


@contextmanager
def _root_logger_kept() -> Iterator[None]:
    """Undo any handler or level the block gives the root logger.

    MCPServer configures the root logger when it is built and none is set. That handler would
    print every library's INFO lines, including the HTTP client's, which hold the coordinates
    sent to NASA POWER, and repeat the request log (spec 11, "Security and privacy").
    """
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    try:
        yield
    finally:
        for handler in list(root.handlers):
            if handler not in handlers:
                root.removeHandler(handler)
                handler.close()
        root.setLevel(level)


def _add_tool(
    server: MCPServer, spec: _ToolSpec[Any], get_services: Callable[[], Services]
) -> None:
    async def call(**arguments: object) -> CallToolResult:
        inp = spec.input_model.model_validate(arguments)
        try:
            return await spec.run(inp, get_services().tool_context())
        except AppError as error:
            return _error_result(error.message)

    # The SDK builds the tool's input schema, and validates the arguments, from the function's
    # signature. One keyword parameter per field of the input model, carrying that field's
    # constraints and alias, makes both the model's own; a Python parameter cannot be named
    # "from" itself. The SDK passes each argument under its alias, hence **arguments.
    call.__name__ = spec.name
    call.__signature__ = inspect.Signature(
        [
            inspect.Parameter(
                name, inspect.Parameter.KEYWORD_ONLY, default=field, annotation=field.annotation
            )
            for name, field in spec.input_model.model_fields.items()
        ],
        return_annotation=(
            CallToolResult if spec.output is None else Annotated[CallToolResult, spec.output]
        ),
    )
    server.add_tool(call, name=spec.name, description=spec.description, annotations=READ_ONLY)


def transport_security(public_base_url: str | None) -> TransportSecuritySettings:
    """The Host and Origin headers /mcp accepts (spec 9).

    Loopback hosts are always allowed, and the host of `public_base_url` when it is set. A
    request with another Host gets 421 and one with another Origin gets 403. A request without
    an Origin header, as sent by a server-side MCP client, passes.
    """
    hosts = list(LOOPBACK_HOSTS)
    origins = [f"{LOOPBACK_SCHEME}://{host}" for host in LOOPBACK_HOSTS]
    if public_base_url is not None:
        public = urlsplit(public_base_url.lower())
        hosts.append(public.netloc)
        origins.append(f"{public.scheme}://{public.netloc}")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[*hosts, *(host + ANY_PORT for host in hosts)],
        allowed_origins=[*origins, *(origin + ANY_PORT for origin in origins)],
    )


def create_http_app(server: MCPServer, public_base_url: str | None) -> Starlette:
    """The SDK's Streamable HTTP app for `server` at /mcp, taking POST only.

    Each request stands alone and is answered with JSON: the tools keep no state between calls
    and send no progress, so neither sessions nor event streams are needed. Every other method
    gets 405. A client that leaves before its request has arrived raises ClientDisconnect, as on
    /api/chat. The host app must enter `server.session_manager.run()` in its lifespan.
    """
    app = server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        stateless_http=True,
        json_response=True,
        transport_security=transport_security(public_base_url),
    )
    for route in app.router.routes:
        if isinstance(route, Route) and route.path == MCP_PATH:
            route.app = _DisconnectGuard(route.app)
    # The SDK's route takes every method, so the refusal goes in front of it.
    app.router.routes.insert(0, Route(MCP_PATH, _refuse_method, methods=MCP_REFUSED_METHODS))
    return app


async def _refuse_method(request: Request) -> NoReturn:
    """Any method on /mcp but POST: 405 with `Allow: POST` (spec 9).

    A GET would open an event stream and a DELETE would end a session; this stateless server
    offers neither, and the SDK's own 405 for them has the wrong shape and `Allow` header.
    """
    raise StarletteHTTPException(
        HTTPStatus.METHOD_NOT_ALLOWED, headers={"Allow": MCP_ALLOWED_METHODS}
    )


class _DisconnectGuard:
    """Raises ClientDisconnect when the client leaves before its request body has arrived.

    The SDK reads the body inside its own error handler, which would log the disconnect with its
    traceback and answer 500. Raised here, it reaches the host app's request log instead, which
    records a closed request and answers no one. The SDK still reads the body, within its limit.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        body_complete = False

        async def guarded_receive() -> Message:
            nonlocal body_complete
            message = await receive()
            if message["type"] == "http.disconnect" and not body_complete:
                raise ClientDisconnect
            if message["type"] == "http.request" and not message.get("more_body", False):
                body_complete = True
            return message

        await self.app(scope, guarded_receive, send)
