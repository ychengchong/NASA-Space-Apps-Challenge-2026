"""The REST adapter of spec 10. Translation only, no analysis.

Each /api endpoint parses its query string into a tool input, calls one tool and returns the
result. The module also maps every error of the app to the JSON shape of spec 10:
{"error": {"code": ..., "message": ...}}.
"""

import csv
import io
from collections.abc import Mapping
from http import HTTPStatus
from pathlib import Path
from typing import Annotated, get_args

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.case_query import (
    QueryValues,
    parse_case_query,
    parse_map_query,
    parse_query_string,
)
from app.config import DATA_DIR
from app.errors import AppError, BadPlaceError, BadRequestError
from app.models import (
    AnalyzeTrendInput,
    Capabilities,
    ComparePlacesInput,
    FindPlaceInput,
    GetSeriesInput,
    Investigation,
    Model,
    PlaceCandidate,
    PlaceInput,
    Resolution,
    SearchVariablesInput,
    Series,
    TrendMap,
    VariableSummary,
)
from app.render import render_case_png
from app.services import Services
from app.tools.places import find_place, round_link_coordinate
from app.tools.series import get_series
from app.tools.trends import analyze_trend, compare_places, map_trends
from app.tools.variables import search_variables

EXAMPLES_PATH = DATA_DIR / "examples.json"

# Error codes beyond the table of spec 10, for answers no tool raises: a path that names
# nothing, and a failure the service did not expect.
NOT_FOUND = "not_found"
INTERNAL_ERROR = "internal_error"
NOT_FOUND_MESSAGE = "There is nothing at this address."
INTERNAL_ERROR_MESSAGE = "Something went wrong on the server. Please try again later."
BAD_REQUEST_MESSAGE = "The request is not valid."

# Spec 10: /api/series takes res and format. These defaults apply when one is left out.
RESOLUTIONS: tuple[str, ...] = get_args(Resolution)
SERIES_FORMATS = ("json", "csv")
DEFAULT_RESOLUTION = "yearly"
DEFAULT_SERIES_FORMAT = "json"
CSV_FORMAT = "csv"
CSV_HEADER = ("date", "value")

router = APIRouter(prefix="/api")


def get_services(request: Request) -> Services:
    """The shared services that main.py stores on the app."""
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]


class ExampleCase(Model):
    """One example case of spec 10; `query` is the case's parameter string."""

    title: str
    teaser: str
    query: str


_EXAMPLE_LIST = TypeAdapter(list[ExampleCase])


def load_examples(path: Path = EXAMPLES_PATH) -> list[ExampleCase]:
    """The example cases in `path`, in file order. A file that holds only whitespace has none.

    Raises pydantic's `ValidationError` when an entry is not a {title, teaser, query} object.
    """
    text = path.read_text(encoding="utf-8")
    if text.strip() == "":
        return []
    return _EXAMPLE_LIST.validate_json(text)


# Endpoints (spec 10)


@router.get("/variables")
async def api_variables(request: Request) -> list[VariableSummary]:
    query = _query_values(request)
    inp = SearchVariablesInput(query=_optional(query, "query"), theme=_optional(query, "theme"))
    return search_variables(inp)


@router.get("/capabilities")
async def api_capabilities(services: ServicesDep) -> Capabilities:
    """Describe user flows without exposing credentials or contacting a provider."""
    return Capabilities(ai_planner_available=services.settings.active_ai_provider is not None)


@router.get("/places")
async def api_places(request: Request) -> list[PlaceCandidate]:
    return find_place(FindPlaceInput(query=_required(_query_values(request), "query")))


@router.get("/case")
async def api_case(request: Request, services: ServicesDep) -> Investigation:
    return await _run_case(parse_case_query(_query_values(request)), services)


@router.get("/series")
async def api_series(request: Request, services: ServicesDep) -> Response:
    query = _query_values(request)
    resolution = _choice(query, "res", RESOLUTIONS, DEFAULT_RESOLUTION)
    output_format = _choice(query, "format", SERIES_FORMATS, DEFAULT_SERIES_FORMAT)
    inp = _series_input(query, resolution)
    series = await get_series(inp, services.tool_context())
    if output_format == CSV_FORMAT:
        return _csv_response(series, inp.place)
    return Response(content=series.model_dump_json(), media_type="application/json")


@router.get("/map")
async def api_map(request: Request, services: ServicesDep) -> TrendMap:
    return await map_trends(parse_map_query(_query_values(request)), services.tool_context())


@router.get("/chart.png")
async def api_chart_png(request: Request, services: ServicesDep) -> Response:
    investigation = await _run_case(parse_case_query(_query_values(request)), services)
    # Drawing is CPU work that would hold up every other request, so it runs in a worker thread.
    png = await run_in_threadpool(render_case_png, investigation)
    return Response(content=png, media_type="image/png")


@router.get("/examples")
async def api_examples() -> list[ExampleCase]:
    return load_examples()


@router.get("/evidence/{identity}")
async def api_evidence(identity: str, services: ServicesDep) -> Response:
    """Download checksum-verified retained bytes; a missing pinned object never refreshes live."""
    return Response(
        content=services.cache.snapshots.get(identity),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{identity}.json"'},
    )


# Query string parsing


def _query_values(request: Request) -> dict[str, list[str]]:
    return parse_query_string(request.url.query)


def _optional(query: QueryValues, name: str) -> str | None:
    """The one value given for `name`, stripped, or None when it is absent or blank."""
    values = query.get(name, [])
    if len(values) > 1:
        raise BadRequestError(f"Give '{name}' only once.")
    if not values or values[0].strip() == "":
        return None
    return values[0].strip()


def _required(query: QueryValues, name: str) -> str:
    value = _optional(query, name)
    if value is None:
        raise BadRequestError(f"The parameter '{name}' is missing.")
    return value


def _choice(query: QueryValues, name: str, allowed: tuple[str, ...], default: str) -> str:
    value = _optional(query, name)
    if value is None:
        return default
    if value not in allowed:
        raise BadRequestError(f"'{name}' must be one of {', '.join(allowed)}.")
    return value


def _series_input(query: QueryValues, resolution: str) -> GetSeriesInput:
    """A series takes the parameters of a one-place case, so it reuses the case parser."""
    case = parse_case_query(query)
    if not isinstance(case, AnalyzeTrendInput):
        raise BadPlaceError("A series is for one place: give p only once.")
    return GetSeriesInput.model_validate(
        {**case.model_dump(exclude={"scan"}), "resolution": resolution}
    )


async def _run_case(
    inp: AnalyzeTrendInput | ComparePlacesInput, services: Services
) -> Investigation:
    ctx = services.tool_context()
    if isinstance(inp, ComparePlacesInput):
        return await compare_places(inp, ctx)
    return await analyze_trend(inp, ctx)


# CSV download


def _csv_response(series: Series, place: PlaceInput) -> Response:
    filename = (
        f"{series.variable.id}_{_filename_coordinate(place.lat)}_"
        f"{_filename_coordinate(place.lon)}_{series.resolution}.csv"
    )
    return Response(
        content=_series_csv(series),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _series_csv(series: Series) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    for value in series.values:
        # A missing value is an empty cell, never 0 or -999.
        writer.writerow([value.date, "" if value.value is None else value.value])
    return buffer.getvalue()


def _filename_coordinate(x: float) -> str:
    """The coordinate as a case link writes it: two decimals at most, such as 60.17 or 25."""
    return f"{round_link_coordinate(x):g}"


# Errors (spec 10, "Errors")


def error_response(
    code: str, message: str, status_code: int, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    """An error in the shape of spec 10: {"error": {"code": ..., "message": ...}}."""
    return JSONResponse(
        {"error": {"code": code, "message": message}}, status_code=status_code, headers=headers
    )


def app_error_response(error: AppError) -> JSONResponse:
    return error_response(error.code, error.message, error.http_status)


def internal_error_response() -> JSONResponse:
    return error_response(INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE, HTTPStatus.INTERNAL_SERVER_ERROR)


def add_error_handlers(app: FastAPI) -> None:
    """Answer tool errors, invalid requests and unknown paths in the error shape of spec 10.

    An unexpected exception is not handled here: main.py turns it into `internal_error`.
    """
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)


async def _app_error(request: Request, exc: AppError) -> JSONResponse:
    return app_error_response(exc)


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # The framework's own answer lists the validator's internals; spec 10 asks for a plain message.
    return error_response(BadRequestError.code, BAD_REQUEST_MESSAGE, BadRequestError.http_status)


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Errors the framework raises itself: an unknown path, or a method a path does not take."""
    if exc.status_code == HTTPStatus.NOT_FOUND:
        return error_response(NOT_FOUND, NOT_FOUND_MESSAGE, exc.status_code, exc.headers)
    status = HTTPStatus(exc.status_code)
    code = BadRequestError.code if status < HTTPStatus.INTERNAL_SERVER_ERROR else INTERNAL_ERROR
    return error_response(code, f"{status.phrase}.", exc.status_code, exc.headers)
