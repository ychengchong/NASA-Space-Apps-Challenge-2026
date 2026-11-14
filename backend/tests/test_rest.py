from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import NoReturn

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.adapters import rest
from app.adapters.case_query import parse_case_query, parse_map_query, parse_query_string
from app.adapters.rest import ExampleCase, load_examples
from app.cache import Cache
from app.catalogue import get_entry, load_catalogue, to_summary
from app.errors import SourceUnavailableError
from app.main import create_app
from app.models import (
    AnalyzeTrendInput,
    Cell,
    ComparePlacesInput,
    Investigation,
    MapCell,
    MapTrendsInput,
    Place,
    PlaceInput,
    PlaceResult,
    Requested,
    SearchVariablesInput,
    TrendMap,
    Verdict,
)
from app.services import Services
from app.sources.base import MonthlyValues, PointSeries
from app.tools.context import ToolContext
from app.tools.trends import AREA_MEAN_NAME, analyze_trend, compare_places
from app.tools.variables import search_variables
from tests.app_client import BASE_URL, make_services
from tests.fake_source import FakeSource, line, monthly_from_yearly

HELSINKI = PlaceInput(lat=60.17, lon=24.94, name="Helsinki")
NAIROBI = PlaceInput(lat=-1.29, lon=36.82, name="Nairobi")
HELSINKI_CASE = "v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual"
HELSINKI_SERIES = "v=air_temp&p=60.17,24.94"
# Whole numbers, so every mean is exact: the value of year Y is Y - 1971.
RISING = monthly_from_yearly(line(1.0))
PNG = b"\x89PNG\r\n\x1a\nnot a real chart"


class UnavailableSource(FakeSource):
    """A source that never answers and has nothing cached."""

    async def point_series(
        self, lat: float, lon: float, codes: Sequence[str], end_year: int
    ) -> dict[str, PointSeries]:
        raise SourceUnavailableError("NASA POWER did not answer and the data is not cached.")


def with_missing_month(year: int, month: int) -> MonthlyValues:
    monthly = monthly_from_yearly(line(1.0))
    monthly[(year, month)] = None
    return monthly


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[Cache]:
    cache = Cache(tmp_path / "cache.sqlite")
    yield cache
    cache.close()


@pytest.fixture
def services(cache: Cache) -> Services:
    return make_services(cache, FakeSource(RISING))


def client_for(services: Services, tmp_path: Path) -> TestClient:
    """A client for the API alone: the static folder holds no web app."""
    return TestClient(create_app(services, static_dir=tmp_path / "no_web_app"))


@pytest.fixture
def client(services: Services, tmp_path: Path) -> TestClient:
    return client_for(services, tmp_path)


def tool_investigation(
    inp: AnalyzeTrendInput | ComparePlacesInput, services: Services
) -> Investigation:
    """What the tool layer itself answers for the case, to compare with the endpoint."""

    async def run() -> Investigation:
        ctx = services.tool_context()
        if isinstance(inp, ComparePlacesInput):
            return await compare_places(inp, ctx)
        return await analyze_trend(inp, ctx)

    return anyio.run(run)


def assert_error(response: httpx.Response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert list(body) == ["error"]
    assert body["error"]["code"] == code
    assert set(body["error"]) == {"code", "message"}
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"] != ""


# /api/variables


def test_variables_returns_the_search_variables_result(client: TestClient) -> None:
    response = client.get("/api/variables?query=rain")

    assert response.status_code == 200
    expected = search_variables(SearchVariablesInput(query="rain"))
    assert response.json() == [summary.model_dump(mode="json") for summary in expected]
    assert response.json()[0]["id"] == "precipitation"


def test_variables_without_query_lists_the_whole_catalogue(client: TestClient) -> None:
    response = client.get("/api/variables")

    assert [summary["id"] for summary in response.json()] == [
        entry.id for entry in load_catalogue()
    ]


def test_variables_keeps_only_the_given_theme(client: TestClient) -> None:
    response = client.get("/api/variables?theme=temperature")

    themes = {summary["theme"] for summary in response.json()}
    assert themes == {"temperature"}


def test_parameter_given_twice_is_a_bad_request(client: TestClient) -> None:
    response = client.get("/api/variables?query=rain&query=wind")

    assert_error(response, 400, "bad_request")


# /api/places


def test_places_finds_a_place_by_name(client: TestClient) -> None:
    response = client.get("/api/places?query=Helsinki")

    assert response.status_code == 200
    first = response.json()[0]
    assert first["name"] == "Helsinki"
    assert set(first) == {"name", "country", "lat", "lon", "kind", "region_type"}


def test_places_without_query_is_a_bad_request(client: TestClient) -> None:
    response = client.get("/api/places?query=")

    assert_error(response, 400, "bad_request")


# /api/case


def test_case_with_one_place_returns_the_analyze_trend_investigation(
    client: TestClient, services: Services
) -> None:
    response = client.get(f"/api/case?{HELSINKI_CASE}")

    assert response.status_code == 200
    inp = AnalyzeTrendInput.model_validate(
        {"variable": "air_temp", "place": HELSINKI, "from": 1981, "to": 2025}
    )
    expected = tool_investigation(inp, services)
    assert response.json() == expected.model_dump(mode="json")
    assert len(response.json()["results"]) == 1


def test_case_writes_the_first_year_as_from(client: TestClient) -> None:
    response = client.get(f"/api/case?{HELSINKI_CASE}")

    assert response.json()["requested"] == {"from": 1981, "to": 2025, "season": "annual"}


def test_case_with_two_places_returns_the_comparison(
    client: TestClient, services: Services
) -> None:
    response = client.get(
        "/api/case?v=air_temp&p=60.17,24.94&p=-1.29,36.82&label=Helsinki&label=Nairobi"
    )

    assert response.status_code == 200
    inp = ComparePlacesInput(variable="air_temp", places=[HELSINKI, NAIROBI])
    expected = tool_investigation(inp, services)
    assert response.json() == expected.model_dump(mode="json")
    assert [result["place"]["name"] for result in response.json()["results"]] == [
        "Helsinki",
        "Nairobi",
    ]
    assert response.json()["summary"] is not None


def test_case_with_scan_includes_the_period_scan(client: TestClient) -> None:
    response = client.get(f"/api/case?{HELSINKI_CASE}&scan=1")

    assert response.json()["results"][0]["trend"]["scan"] is not None


# /api/series


def test_series_defaults_to_yearly_json(client: TestClient) -> None:
    response = client.get(f"/api/series?{HELSINKI_SERIES}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body["resolution"] == "yearly"
    assert body["variable"]["id"] == "air_temp"
    assert len(body["values"]) == 45
    assert body["values"][0] == {"date": "1981", "value": 10.0}


def test_series_monthly_lists_each_month(client: TestClient) -> None:
    response = client.get(f"/api/series?{HELSINKI_SERIES}&from=2024&to=2025&res=monthly")

    values = response.json()["values"]
    assert len(values) == 24
    assert values[0] == {"date": "2024-01", "value": 53.0}


def test_series_json_keeps_a_missing_month_as_null(cache: Cache, tmp_path: Path) -> None:
    client = client_for(make_services(cache, FakeSource(with_missing_month(2000, 12))), tmp_path)

    response = client.get(f"/api/series?{HELSINKI_SERIES}&from=2000&to=2000&res=monthly")

    assert response.json()["values"][11] == {"date": "2000-12", "value": None}


def test_series_csv_has_a_header_and_one_row_per_value(client: TestClient) -> None:
    response = client.get(f"/api/series?{HELSINKI_SERIES}&from=2024&to=2025&format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines() == ["date,value", "2024,53.0", "2025,54.0"]


def test_series_csv_leaves_a_missing_month_empty(cache: Cache, tmp_path: Path) -> None:
    client = client_for(make_services(cache, FakeSource(with_missing_month(2000, 12))), tmp_path)

    response = client.get(f"/api/series?{HELSINKI_SERIES}&from=2000&to=2000&res=monthly&format=csv")

    rows = response.text.splitlines()
    assert rows[12] == "2000-12,"
    assert rows[11] == "2000-11,29.0"


def test_series_csv_leaves_a_year_with_a_missing_month_empty(cache: Cache, tmp_path: Path) -> None:
    client = client_for(make_services(cache, FakeSource(with_missing_month(2000, 12))), tmp_path)

    response = client.get(f"/api/series?{HELSINKI_SERIES}&from=1999&to=2001&format=csv")

    assert response.text.splitlines() == ["date,value", "1999,28.0", "2000,", "2001,30.0"]


@pytest.mark.parametrize(
    ("query", "filename"),
    [
        ("v=air_temp&p=60.17,24.94", "air_temp_60.17_24.94_yearly.csv"),
        ("v=precipitation&p=-1.29,36.82&res=monthly", "precipitation_-1.29_36.82_monthly.csv"),
    ],
)
def test_series_csv_is_an_attachment_named_after_variable_point_and_resolution(
    client: TestClient, query: str, filename: str
) -> None:
    response = client.get(f"/api/series?{query}&format=csv")

    assert response.headers["content-disposition"] == f'attachment; filename="{filename}"'


def test_series_takes_one_place(client: TestClient) -> None:
    response = client.get("/api/series?v=air_temp&p=60.17,24.94&p=-1.29,36.82")

    assert_error(response, 400, "bad_place")


@pytest.mark.parametrize("parameter", ["res=weekly", "format=xml"])
def test_series_with_an_unknown_option_is_a_bad_request(client: TestClient, parameter: str) -> None:
    response = client.get(f"/api/series?{HELSINKI_SERIES}&{parameter}")

    assert_error(response, 400, "bad_request")


# /api/map


def trend_map_for(inp: MapTrendsInput) -> TrendMap:
    """A small TrendMap, so the adapter is tested apart from the region analysis."""
    cell = Cell(lat=60.0, lon=25.0, height=10.0, width=10.0)
    return TrendMap(
        variable=to_summary(get_entry(inp.variable)),
        requested=Requested.model_validate({"from": 1991, "to": 2020, "season": "JJA"}),
        box=inp.box,
        cells=[MapCell(lat=60.0, lon=25.0, sen_slope=None, mk_p=None, significant=False)],
        area_mean=PlaceResult(
            place=Place(name=AREA_MEAN_NAME, lat=60.0, lon=25.0, cell=cell),
            series=[],
            trend=None,
            verdict=Verdict(kind="no_data", direction=None, sentence="No data.", cautions=[]),
        ),
        steps=[],
        sources=[],
        app_url=f"{BASE_URL}/map",
    )


def test_map_passes_the_parsed_query_to_map_trends(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[MapTrendsInput] = []

    async def fake_map_trends(inp: MapTrendsInput, ctx: ToolContext) -> TrendMap:
        received.append(inp)
        return trend_map_for(inp)

    monkeypatch.setattr(rest, "map_trends", fake_map_trends)
    query = "v=air_temp&from=1991&to=2020&s=JJA&box=55,20,65,30"

    response = client.get(f"/api/map?{query}")

    assert response.status_code == 200
    assert received == [parse_map_query(parse_query_string(query))]
    assert response.json() == trend_map_for(received[0]).model_dump(mode="json")


def test_map_with_a_malformed_box_is_a_bad_place(client: TestClient) -> None:
    response = client.get("/api/map?v=air_temp&box=55,20,65")

    assert_error(response, 400, "bad_place")


# /api/chart.png


def test_chart_png_draws_the_case_investigation(
    client: TestClient, services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    drawn: list[Investigation] = []

    def fake_render(investigation: Investigation) -> bytes:
        drawn.append(investigation)
        return PNG

    monkeypatch.setattr(rest, "render_case_png", fake_render)

    response = client.get(f"/api/chart.png?{HELSINKI_CASE}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG
    inp = parse_case_query(parse_query_string(HELSINKI_CASE))
    assert drawn == [tool_investigation(inp, services)]


# /api/examples


def test_examples_returns_the_committed_examples(client: TestClient) -> None:
    response = client.get("/api/examples")

    assert response.status_code == 200
    assert response.json() == [example.model_dump(mode="json") for example in load_examples()]


def test_load_examples_reads_title_teaser_and_query(tmp_path: Path) -> None:
    path = tmp_path / "examples.json"
    path.write_text(
        '[{"title": "Warming", "teaser": "A clear trend.", "query": "v=air_temp&p=1,2"}]',
        encoding="utf-8",
    )

    assert load_examples(path) == [
        ExampleCase(title="Warming", teaser="A clear trend.", query="v=air_temp&p=1,2")
    ]


@pytest.mark.parametrize("text", ["", "  \n", "[]"])
def test_load_examples_of_an_empty_file_is_an_empty_list(tmp_path: Path, text: str) -> None:
    path = tmp_path / "examples.json"
    path.write_text(text, encoding="utf-8")

    assert load_examples(path) == []


def test_load_examples_rejects_an_entry_without_a_query(tmp_path: Path) -> None:
    path = tmp_path / "examples.json"
    path.write_text('[{"title": "Warming", "teaser": "A clear trend."}]', encoding="utf-8")

    with pytest.raises(ValidationError):
        load_examples(path)


# Errors (spec 10)


@pytest.mark.parametrize(
    ("query", "code"),
    [
        ("v=no_such_variable&p=60.17,24.94", "unknown_variable"),
        ("v=air_temp&p=95,24.94", "bad_place"),
        ("v=air_temp&p=60.17,24.94&p=1,1&p=2,2&p=3,3&p=4,4", "bad_place"),
        ("v=air_temp&p=60.17,24.94&from=2030&to=2031", "bad_period"),
        ("v=air_temp&p=60.17,24.94&s=winter", "bad_request"),
        ("p=60.17,24.94", "bad_request"),
    ],
)
def test_invalid_case_is_answered_with_its_spec_code(
    client: TestClient, query: str, code: str
) -> None:
    response = client.get(f"/api/case?{query}")

    assert_error(response, 400, code)


def test_unknown_api_path_is_not_found(client: TestClient) -> None:
    response = client.get("/api/nope")

    assert_error(response, 404, "not_found")


def test_wrong_method_is_refused_in_the_error_shape(client: TestClient) -> None:
    response = client.post(f"/api/case?{HELSINKI_CASE}")

    assert_error(response, 405, "bad_request")
    assert response.headers["allow"] == "GET"


def test_unreachable_source_is_source_unavailable(cache: Cache, tmp_path: Path) -> None:
    client = client_for(make_services(cache, UnavailableSource()), tmp_path)

    response = client.get(f"/api/case?{HELSINKI_CASE}")

    assert_error(response, 502, "source_unavailable")
    assert response.json()["error"]["message"] == (
        "NASA POWER did not answer and the data is not cached."
    )


class ProbeBody(BaseModel):
    text: str


async def probe(body: ProbeBody) -> dict[str, str]:
    return {"text": body.text}


def test_framework_validation_error_is_a_plain_bad_request(
    services: Services, tmp_path: Path
) -> None:
    app = create_app(services, static_dir=tmp_path / "no_web_app")
    app.add_api_route("/api/probe", probe, methods=["POST"])

    response = TestClient(app).post("/api/probe", json={"text": ["not", "text"]})

    assert_error(response, 400, "bad_request")
    assert response.json()["error"]["message"] == "The request is not valid."


def test_unexpected_error_is_internal_error_without_details(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_search(inp: SearchVariablesInput) -> NoReturn:
        raise RuntimeError("secret detail")

    monkeypatch.setattr(rest, "search_variables", broken_search)

    response = client.get("/api/variables")

    assert_error(response, 500, "internal_error")
    assert "secret detail" not in response.text
    assert "Traceback" not in response.text
