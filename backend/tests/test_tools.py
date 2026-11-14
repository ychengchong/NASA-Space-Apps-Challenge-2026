import json
from datetime import date
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest

from app.cache import Cache
from app.errors import BadPeriodError, UnknownVariableError
from app.models import (
    AnalyzeTrendInput,
    ComparePlacesInput,
    GetSeriesInput,
    Investigation,
    PlaceInput,
)
from app.sources.base import MonthKey, PointSeries
from app.sources.power import CACHE_SOURCE, PowerClient, parse_monthly
from app.tools.context import ToolContext
from app.tools.places import snap_to_grid
from app.tools.series import get_series
from app.tools.trends import analyze_trend, compare_places
from tests.fake_source import FakeSource, GatedSource, line, monthly_from_yearly

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).parent / "fixtures"
LAST_COMPLETE_YEAR = 2025
BASE_URL = "https://trend.example"

HELSINKI = PlaceInput(lat=60.17, lon=24.94, name="Helsinki")
NAIROBI = PlaceInput(lat=-1.29, lon=36.82, name="Nairobi")
HELSINKI_GRID_POINT = (60.0, 25.0)
# Spec 6: sunlight and cloud at Helsinki come from the 1° cell from 60° to 61° N, 24° to 25° E.
HELSINKI_ONE_DEGREE_CENTRE = (60.5, 24.5)
NAIROBI_GRID_POINT = snap_to_grid(NAIROBI.lat, NAIROBI.lon)

RISING = monthly_from_yearly(line(0.05))
FALLING = monthly_from_yearly(line(-0.05))
FLAT = monthly_from_yearly(dict.fromkeys(range(1981, 2026), 1.0))
# The catalogue codes on each grid, in catalogue order (spec 6, "Starter catalogue").
MERRA2_CODES = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "TS",
    "PRECTOTCORR",
    "RH2M",
    "QV2M",
    "WS10M",
    "GWETTOP",
    "GWETROOT",
)
ONE_DEGREE_CODES = ("ALLSKY_SFC_SW_DWN", "CLOUD_AMT")


def saved_t2m(name: str) -> dict[MonthKey, float | None]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return parse_monthly(payload["properties"]["parameter"]["T2M"], payload["header"]["fill_value"])


def codes_of(request: httpx.Request) -> list[str]:
    return request.url.params["parameters"].split(",")


def context(source: FakeSource, public_base_url: str | None = None) -> ToolContext:
    return ToolContext(
        source=source, last_complete_year=LAST_COMPLETE_YEAR, public_base_url=public_base_url
    )


def trend_input(**fields: Any) -> AnalyzeTrendInput:
    return AnalyzeTrendInput.model_validate({"variable": "air_temp", "place": HELSINKI, **fields})


def compare_input(*places: PlaceInput, **fields: Any) -> ComparePlacesInput:
    return ComparePlacesInput.model_validate(
        {"variable": "air_temp", "places": list(places), **fields}
    )


def series_input(**fields: Any) -> GetSeriesInput:
    return GetSeriesInput.model_validate({"variable": "air_temp", "place": HELSINKI, **fields})


async def analyse(source: FakeSource, **fields: Any) -> Investigation:
    return await analyze_trend(trend_input(**fields), context(source))


# Period (spec 7, step 1)


async def test_period_defaults_to_the_full_record_and_annual() -> None:
    investigation = await analyse(FakeSource(RISING))

    assert investigation.requested.model_dump() == {"from": 1981, "to": 2025, "season": "annual"}
    assert [point.year for point in investigation.results[0].series] == list(range(1981, 2026))


async def test_period_is_clamped_to_the_record_and_the_last_complete_year() -> None:
    with pytest.raises(BadPeriodError, match="dates were not changed"):
        await analyse(FakeSource(RISING), **{"from": 1950, "to": 2100})


async def test_period_starts_at_the_variables_own_record_start() -> None:
    investigation = await analyse(FakeSource(RISING), variable="sunlight")

    assert investigation.requested.from_ == 1984


@pytest.mark.parametrize(
    "period",
    [
        {"from": 2020, "to": 2010},
        {"from": 2030},
        {"to": 1975},
    ],
)
async def test_period_without_years_after_clamping_raises_bad_period(
    period: dict[str, int],
) -> None:
    with pytest.raises(BadPeriodError):
        await analyse(FakeSource(RISING), **period)


async def test_period_before_a_late_record_start_raises_bad_period() -> None:
    with pytest.raises(BadPeriodError):
        await analyse(FakeSource(RISING), variable="sunlight", to=1983)


async def test_unknown_variable_raises_before_any_fetch() -> None:
    source = FakeSource(RISING)

    with pytest.raises(UnknownVariableError):
        await analyse(source, variable="T2M")
    assert source.calls == []


# Fetching


async def test_place_is_fetched_at_its_grid_point_for_the_whole_record() -> None:
    source = FakeSource(RISING)

    await analyse(source, **{"from": 2000, "to": 2010})

    assert [(lat, lon, end_year) for lat, lon, _, end_year in source.calls] == [
        (*HELSINKI_GRID_POINT, LAST_COMPLETE_YEAR)
    ]


@pytest.mark.parametrize("variable", ["air_temp", "precipitation"])
async def test_merra2_variable_asks_only_for_the_merra2_codes_at_the_grid_point(
    variable: str,
) -> None:
    source = FakeSource(RISING)

    await analyse(source, variable=variable)

    assert source.calls == [(*HELSINKI_GRID_POINT, MERRA2_CODES, LAST_COMPLETE_YEAR)]


@pytest.mark.parametrize("variable", ["sunlight", "cloud_cover"])
async def test_one_degree_variable_asks_only_for_the_one_degree_codes_at_its_cell_centre(
    variable: str,
) -> None:
    source = FakeSource(RISING)

    await analyse(source, variable=variable)

    assert source.calls == [(*HELSINKI_ONE_DEGREE_CENTRE, ONE_DEGREE_CODES, LAST_COMPLETE_YEAR)]


async def test_series_of_a_one_degree_variable_is_fetched_at_its_cell_centre() -> None:
    source = FakeSource(RISING)

    series = await get_series(
        series_input(variable="cloud_cover", resolution="yearly"), context(source)
    )

    assert (series.place.cell.lat, series.place.cell.lon) == HELSINKI_ONE_DEGREE_CENTRE
    assert source.calls == [(*HELSINKI_ONE_DEGREE_CENTRE, ONE_DEGREE_CODES, LAST_COMPLETE_YEAR)]


async def test_result_comes_from_the_analysed_variables_own_series() -> None:
    source = FakeSource(RISING, by_code={"PRECTOTCORR": FALLING})

    precipitation = (await analyse(source, variable="precipitation")).results[0]
    air_temp = (await analyse(source)).results[0]

    assert precipitation.trend.sen_slope < 0
    assert precipitation.verdict.kind == "inference_unavailable"
    assert air_temp.verdict.direction == "rising"


async def test_place_reports_requested_point_and_grid_cell() -> None:
    place = (await analyse(FakeSource(RISING))).results[0].place

    assert (place.name, place.lat, place.lon) == ("Helsinki", 60.17, 24.94)
    assert place.cell.model_dump() == {"lat": 60.0, "lon": 25.0, "height": 0.5, "width": 0.625}


async def test_unnamed_place_is_named_by_its_grid_point() -> None:
    investigation = await analyse(FakeSource(RISING), place={"lat": 60.17, "lon": 24.94})
    result = investigation.results[0]

    assert result.place.name == "60.0°N, 25.0°E"
    assert "grid cell containing 60.0°N, 25.0°E" in result.verdict.sentence


# Results (spec 7, steps 2 to 9)


async def test_clear_rise_is_significant_with_the_rate_per_decade() -> None:
    result = (await analyse(FakeSource(RISING))).results[0]

    assert result.trend is not None
    assert result.trend.sen_slope == pytest.approx(0.5)
    assert result.verdict.kind == "significant"
    assert "+0.50 °C per decade" in result.verdict.sentence
    assert "conditional on its assumptions" in result.verdict.sentence


async def test_year_with_a_missing_month_stays_in_the_series_but_not_in_the_test() -> None:
    monthly = dict(RISING)
    monthly[(2000, 7)] = None

    result = (await analyse(FakeSource(monthly))).results[0]

    assert result.series[2000 - 1981].model_dump() == {"year": 2000, "value": None}
    assert len(result.series) == 45
    assert result.trend is not None
    assert result.trend.n == 44


async def test_fewer_than_ten_years_gives_too_few_years_and_no_trend() -> None:
    result = (await analyse(FakeSource(RISING), **{"from": 2016, "to": 2024})).results[0]

    assert result.verdict.kind == "too_few_years"
    assert result.verdict.direction is None
    assert result.trend is None
    assert len(result.series) == 9


async def test_ten_years_are_enough_to_test() -> None:
    result = (await analyse(FakeSource(RISING), **{"from": 2016, "to": 2025})).results[0]

    assert result.trend is not None
    assert result.trend.n == 10


async def test_all_months_missing_gives_no_data_and_no_trend() -> None:
    all_missing = monthly_from_yearly(dict.fromkeys(range(1981, 2026)))

    result = (await analyse(FakeSource(all_missing))).results[0]

    assert result.verdict.kind == "no_data"
    assert result.trend is None
    assert all(point.value is None for point in result.series)
    assert len(result.series) == 45


async def test_place_with_no_record_at_all_gives_no_data() -> None:
    result = (await analyse(FakeSource({}))).results[0]

    assert result.verdict.kind == "no_data"
    assert result.trend is None


async def test_constant_values_give_a_zero_slope_without_direction() -> None:
    result = (await analyse(FakeSource(FLAT), variable="surface_soil_wetness")).results[0]

    assert result.trend is not None
    assert result.trend.sen_slope == 0
    assert result.trend.mk_p is None
    assert result.verdict.kind == "inference_unavailable"


async def test_yearly_values_match_the_saved_response() -> None:
    result = (
        await analyse(FakeSource(saved_t2m("power_point_gap.json")), **{"from": 2000, "to": 2005})
    ).results[0]

    assert [point.value for point in result.series] == [
        pytest.approx(6.460027322404371),
        pytest.approx(5.529068493150685),
        None,
        pytest.approx(4.778109589041096),
        pytest.approx(5.53827868852459),
        pytest.approx(6.71131506849315),
    ]


async def test_december_counts_toward_the_following_year() -> None:
    result = (
        await analyse(
            FakeSource(saved_t2m("power_point_gap.json")),
            **{"from": 2000, "to": 2005, "season": "DJF"},
        )
    ).results[0]

    assert [point.value for point in result.series] == [
        None,
        pytest.approx(-2.2447777777777778),
        pytest.approx(-3.3435555555555556),
        None,
        pytest.approx(-3.753736263736264),
        pytest.approx(-0.6898888888888888),
    ]


async def test_first_djf_value_of_the_record_is_1982() -> None:
    result = (await analyse(FakeSource(RISING), season="DJF")).results[0]

    assert result.series[0].model_dump() == {"year": 1981, "value": None}
    assert result.trend is not None
    assert result.trend.first_year == 1982


async def test_scan_is_left_out_unless_asked_for() -> None:
    trend = (await analyse(FakeSource(RISING))).results[0].trend

    assert trend is not None
    assert trend.scan is None


async def test_scan_has_one_point_per_start_year_that_leaves_ten_years() -> None:
    trend = (await analyse(FakeSource(RISING), scan=True)).results[0].trend

    assert trend is not None
    assert trend.scan is not None
    assert [point.start for point in trend.scan] == list(range(1981, 2017))


async def test_one_place_has_no_contrast_or_summary() -> None:
    investigation = await analyse(FakeSource(RISING))

    assert investigation.contrast is None
    assert investigation.summary is None


# compare_places (spec 7, "Comparing places")


async def compare(
    helsinki: dict[MonthKey, float | None], nairobi: dict[MonthKey, float | None]
) -> Investigation:
    source = FakeSource(by_point={HELSINKI_GRID_POINT: helsinki, NAIROBI_GRID_POINT: nairobi})
    return await compare_places(compare_input(HELSINKI, NAIROBI), context(source))


async def test_significant_rise_and_fall_are_opposite_directions() -> None:
    investigation = await compare(RISING, FALLING)

    assert investigation.common_years == list(range(1981, 2026))
    assert "identical complete years" in investigation.summary
    assert "not a statistical test of differences" in investigation.summary


async def test_significant_rises_everywhere_are_the_same_direction() -> None:
    investigation = await compare(RISING, RISING)

    assert investigation.common_years == list(range(1981, 2026))
    assert "identical complete years" in investigation.summary
    assert "not a statistical test of differences" in investigation.summary


async def test_a_place_without_a_significant_trend_makes_the_contrast_unclear() -> None:
    investigation = await compare(RISING, FLAT)

    assert investigation.common_years == list(range(1981, 2026))
    assert "identical complete years" in investigation.summary
    assert "not a statistical test of differences" in investigation.summary


async def test_compare_keeps_the_order_of_the_places() -> None:
    investigation = await compare(RISING, FALLING)

    assert [result.place.name for result in investigation.results] == ["Helsinki", "Nairobi"]
    assert [result.verdict.direction for result in investigation.results] == ["rising", "falling"]


async def test_compare_fetches_the_places_at_the_same_time() -> None:
    source = GatedSource(expected=2, monthly=RISING)

    with anyio.fail_after(1):
        await compare_places(compare_input(HELSINKI, NAIROBI), context(source))

    assert len(source.calls) == 2


async def test_places_with_the_same_source_list_it_once() -> None:
    investigation = await compare(RISING, FALLING)

    assert {source.name for source in investigation.sources} == {"NASA POWER (MERRA-2)"}
    assert [source.snapshot_id for source in investigation.sources] == [
        result.snapshot_id for result in investigation.results
    ]


# id and app_url (spec 5 and spec 10, "Case parameters")


async def test_app_url_holds_the_case_parameters_in_spec_order() -> None:
    investigation = await analyze_trend(trend_input(), context(FakeSource(RISING), BASE_URL))

    assert investigation.app_url.startswith(
        "https://trend.example/case?v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual&snap="
    )
    assert investigation.app_url.endswith("&av=td-2026-11-v1")


async def test_app_url_is_a_path_without_a_public_base_url() -> None:
    investigation = await analyse(FakeSource(RISING))

    assert investigation.app_url.startswith("/case?v=air_temp&")


async def test_link_has_no_label_when_no_place_has_a_name() -> None:
    investigation = await analyse(FakeSource(RISING), place={"lat": 60.17, "lon": 24.94})

    assert investigation.app_url.startswith(
        "/case?v=air_temp&p=60.17,24.94&from=1981&to=2025&s=annual&snap="
    )
    assert "label=" not in investigation.app_url


async def test_link_keeps_labels_in_step_with_places() -> None:
    unnamed = PlaceInput(lat=-1.29, lon=36.82)

    investigation = await compare_places(
        compare_input(HELSINKI, unnamed), context(FakeSource(RISING))
    )

    assert "&p=60.17,24.94&p=-1.29,36.82&label=Helsinki&label=&from=" in investigation.app_url


async def test_link_rounds_coordinates_to_two_decimals() -> None:
    investigation = await analyse(FakeSource(RISING), place={"lat": 60.1234, "lon": 24.9})

    assert "&p=60.1234,24.9&" in investigation.app_url


async def test_link_encodes_label_text() -> None:
    place = {"lat": -23.55, "lon": -46.63, "name": "São Paulo & co"}

    investigation = await analyse(FakeSource(RISING), place=place)

    assert "&label=S%C3%A3o%20Paulo%20%26%20co&" in investigation.app_url


async def test_id_is_twelve_hex_digits() -> None:
    investigation = await analyse(FakeSource(RISING))

    assert len(investigation.id) == 64
    assert set(investigation.id) <= set("0123456789abcdef")


async def test_identical_inputs_give_the_same_id_and_link() -> None:
    first = await analyse(FakeSource(RISING))
    second = await analyse(FakeSource(RISING))

    assert (first.id, first.app_url) == (second.id, second.app_url)


@pytest.mark.parametrize(
    "fields",
    [
        {"from": 1950},
        {"to": 2100},
        {"scan": True},
        {"place": {"lat": 60.171, "lon": 24.94, "name": "Helsinki"}},
        {"place": {"lat": 60.17, "lon": 24.94, "name": " Helsinki "}},
    ],
)
async def test_inputs_that_normalise_alike_give_the_same_case(fields: dict[str, Any]) -> None:
    base = await analyse(FakeSource(RISING))
    if fields.get("from", 1981) < 1981 or fields.get("to", 2025) > 2025:
        with pytest.raises(BadPeriodError):
            await analyse(FakeSource(RISING), **fields)
        return
    other = await analyse(FakeSource(RISING), **fields)
    if "place" in fields and fields["place"]["lat"] != HELSINKI.lat:
        assert other.id != base.id
    else:
        assert (other.id, other.app_url) == (base.id, base.app_url)


@pytest.mark.parametrize(
    "fields",
    [
        {"variable": "max_temp"},
        {"place": {"lat": 60.2, "lon": 24.94, "name": "Helsinki"}},
        {"place": {"lat": 60.17, "lon": 24.94, "name": "Helsingfors"}},
        {"place": {"lat": 60.17, "lon": 24.94}},
        {"from": 1990},
        {"to": 2020},
        {"season": "JJA"},
    ],
)
async def test_different_inputs_give_a_different_case(fields: dict[str, Any]) -> None:
    base = await analyse(FakeSource(RISING))
    other = await analyse(FakeSource(RISING), **fields)

    assert other.id != base.id
    assert other.app_url != base.app_url


# Steps and repeatability


async def test_steps_name_variable_grid_point_period_years_and_correction() -> None:
    steps = " ".join((await analyse(FakeSource(saved_t2m("power_point_full.json")))).steps)

    assert "Air temperature (air_temp)" in steps
    assert "60.0°N, 25.0°E, in a cell of 0.5° by 0.625°" in steps
    assert "from 1981 to 2025" in steps
    assert "45 complete years" in steps
    assert "Mann-Kendall" in steps
    assert "mk_mc_envelope_v1" in steps
    assert "correction factor" not in steps


async def test_steps_name_the_one_degree_cell_that_holds_the_place() -> None:
    steps = (await analyse(FakeSource(RISING), variable="sunlight")).steps

    assert steps[1] == (
        "Used the 1° by 1° cell that holds Helsinki (60.17, 24.94), centred on 60.5°N, 24.5°E."
    )


async def test_steps_say_why_no_test_ran_on_a_short_record() -> None:
    steps = (await analyse(FakeSource(RISING), **{"from": 2016, "to": 2024})).steps

    assert "9 complete years" in steps[-1]
    assert "no test was run" in steps[-1]


async def test_steps_say_december_counts_toward_the_following_year() -> None:
    steps = (await analyse(FakeSource(RISING), season="DJF")).steps

    assert any("December counts toward the following year" in step for step in steps)


def power_client(cache: Cache, requests: list[httpx.Request]) -> PowerClient:
    payload = json.loads((FIXTURES / "power_point_full.json").read_text(encoding="utf-8"))

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    return PowerClient(
        cache,
        httpx.AsyncClient(transport=httpx.MockTransport(answer)),
        today=lambda: date(2026, 11, 13),
    )


async def test_investigation_is_identical_whether_or_not_the_data_was_cached(
    tmp_path: Path,
) -> None:
    cache = Cache(tmp_path / "cache.sqlite")
    requests: list[httpx.Request] = []
    first_client = power_client(cache, requests)
    later_client = power_client(cache, requests)
    try:
        fetched = await analyze_trend(trend_input(), ToolContext(first_client, LAST_COMPLETE_YEAR))
        cached = await analyze_trend(trend_input(), ToolContext(first_client, LAST_COMPLETE_YEAR))
        from_file = await analyze_trend(
            trend_input(), ToolContext(later_client, LAST_COMPLETE_YEAR)
        )
    finally:
        await first_client.aclose()
        await later_client.aclose()
        cache.close()

    assert len(requests) == 1
    assert cached.model_dump() == fetched.model_dump()
    assert from_file.model_dump() == fetched.model_dump()


async def test_a_second_variable_at_the_same_place_is_read_from_the_cache(
    tmp_path: Path,
) -> None:
    cache = Cache(tmp_path / "cache.sqlite")
    requests: list[httpx.Request] = []
    client = power_client(cache, requests)
    try:
        await analyze_trend(trend_input(), ToolContext(client, LAST_COMPLETE_YEAR))
        await analyze_trend(
            trend_input(variable="precipitation"), ToolContext(client, LAST_COMPLETE_YEAR)
        )
    finally:
        await client.aclose()
        cache.close()

    assert len(requests) == 1


async def test_each_grid_is_fetched_and_cached_only_at_its_own_cell_centre(
    tmp_path: Path,
) -> None:
    cache = Cache(tmp_path / "cache.sqlite")
    requests: list[httpx.Request] = []
    client = power_client(cache, requests)
    every_code = [*MERRA2_CODES, *ONE_DEGREE_CODES]
    try:
        for variable in ("air_temp", "sunlight", "cloud_cover", "precipitation"):
            await analyze_trend(
                trend_input(variable=variable), ToolContext(client, LAST_COMPLETE_YEAR)
            )
        at_grid_point = cache.read_point_series(
            CACHE_SOURCE, *HELSINKI_GRID_POINT, every_code, LAST_COMPLETE_YEAR
        )
        at_one_degree_centre = cache.read_point_series(
            CACHE_SOURCE, *HELSINKI_ONE_DEGREE_CENTRE, every_code, LAST_COMPLETE_YEAR
        )
    finally:
        await client.aclose()
        cache.close()

    assert [
        (request.url.params["latitude"], request.url.params["longitude"], codes_of(request))
        for request in requests
    ] == [("60.0", "25.0", list(MERRA2_CODES)), ("60.5", "24.5", list(ONE_DEGREE_CODES))]
    assert set(at_grid_point) == set(MERRA2_CODES)
    assert set(at_one_degree_centre) == set(ONE_DEGREE_CODES)


async def test_sources_name_only_the_analysed_variables_own_fetch(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "cache.sqlite")
    cached_earlier = PointSeries(
        code="T2M",
        lat=HELSINKI_GRID_POINT[0],
        lon=HELSINKI_GRID_POINT[1],
        monthly=RISING,
        version="v2.9.0",
        accessed="2026-01-02",
    )
    cache.write_point_series(CACHE_SOURCE, [cached_earlier], LAST_COMPLETE_YEAR)
    client = power_client(cache, [])
    try:
        investigation = await analyze_trend(trend_input(), ToolContext(client, LAST_COMPLETE_YEAR))
    finally:
        await client.aclose()
        cache.close()

    assert [(source.name, source.version, source.accessed) for source in investigation.sources] == [
        ("NASA POWER (MERRA-2)", "v2.9.0", "2026-01-02")
    ]
    assert investigation.sources[0].snapshot_id == investigation.results[0].snapshot_id


# get_series


async def test_monthly_series_lists_every_month_of_the_period() -> None:
    monthly = saved_t2m("power_point_gap.json")

    series = await get_series(
        series_input(resolution="monthly", **{"from": 2001, "to": 2002}),
        context(FakeSource(monthly)),
    )

    assert [point.date for point in series.values] == [
        f"{year}-{month:02d}" for year in (2001, 2002) for month in range(1, 13)
    ]
    assert [point.value for point in series.values[:2]] == [monthly[(2001, 1)], monthly[(2001, 2)]]


async def test_monthly_series_keeps_a_missing_month_as_none() -> None:
    series = await get_series(
        series_input(resolution="monthly", **{"from": 2002, "to": 2002}),
        context(FakeSource(saved_t2m("power_point_gap.json"))),
    )

    assert series.values[-1].model_dump() == {"date": "2002-12", "value": None}


async def test_monthly_djf_series_starts_with_the_previous_december() -> None:
    series = await get_series(
        series_input(resolution="monthly", season="DJF", **{"from": 2001, "to": 2002}),
        context(FakeSource(saved_t2m("power_point_gap.json"))),
    )

    assert [point.date for point in series.values] == [
        "2000-12",
        "2001-01",
        "2001-02",
        "2001-12",
        "2002-01",
        "2002-02",
    ]
    assert series.values[0].value == pytest.approx(1.08)


async def test_yearly_series_holds_the_yearly_means() -> None:
    series = await get_series(
        series_input(resolution="yearly", **{"from": 2000, "to": 2005}),
        context(FakeSource(saved_t2m("power_point_gap.json"))),
    )

    assert [point.date for point in series.values] == [str(y) for y in range(2000, 2006)]
    assert series.values[0].value == pytest.approx(6.460027322404371)
    assert series.values[2].value is None


async def test_series_reports_variable_place_and_resolution() -> None:
    series = await get_series(series_input(resolution="yearly"), context(FakeSource(RISING)))

    assert series.variable.id == "air_temp"
    assert series.place.cell.lat == 60.0
    assert series.resolution == "yearly"
    assert len(series.values) == 45


async def test_series_period_without_years_raises_bad_period() -> None:
    with pytest.raises(BadPeriodError):
        await get_series(
            series_input(resolution="yearly", **{"from": 2030}), context(FakeSource(RISING))
        )
