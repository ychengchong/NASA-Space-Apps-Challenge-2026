import math
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.cache import Cache
from app.catalogue import get_entry
from app.errors import BadPeriodError, BadPlaceError, UnknownVariableError
from app.models import (
    AnalyzeTrendInput,
    Box,
    Investigation,
    MapCell,
    MapTrendsInput,
    SourceRef,
    TrendMap,
)
from app.sources.base import MonthKey, MonthlyValues
from app.sources.power import POINT_PATH, REGIONAL_PATH, PowerClient
from app.stats import cos_lat_weighted_mean
from app.tools.context import ToolContext
from app.tools.trends import AREA_MEAN_NAME, analyze_trend, map_trends
from tests.fake_source import (
    FAKE_ACCESSED,
    FAKE_VERSION,
    FakeSource,
    GridPoint,
    RegionalFakeSource,
    line,
    monthly_from_yearly,
)

pytestmark = pytest.mark.anyio

LAST_COMPLETE_YEAR = 2025
BASE_URL = "https://trend.example"
BOX = Box(south=55.0, west=20.0, north=65.0, east=30.0)
RECORD_YEARS = range(1981, LAST_COMPLETE_YEAR + 1)

RISING = monthly_from_yearly(line(0.05))
FLAT = monthly_from_yearly(dict.fromkeys(RECORD_YEARS, 1.0))
# A rise with a saw-tooth on top. Its corrected p-value, about 0.013, passes the plain 5% rule
# but not the Benjamini-Hochberg rule once a dozen cells are tested.
MODERATE = monthly_from_yearly(
    {year: 0.01 * k + (3 * k % 11) * 0.1 for k, year in enumerate(RECORD_YEARS)}
)
# Eight complete years, two fewer than a trend test needs.
SHORT = monthly_from_yearly(line(0.05, first_year=2018))
ALL_MISSING = monthly_from_yearly(dict.fromkeys(RECORD_YEARS, None))


def row(n: int, lat: float = 60.0) -> list[GridPoint]:
    """`n` neighbouring grid points along one latitude, from 20.0° east."""
    return [(lat, 20.0 + 0.625 * k) for k in range(n)]


STRONG_POINT, MODERATE_POINT, *OTHER_POINTS = row(12)


def map_input(box: Box = BOX, **fields: Any) -> MapTrendsInput:
    return MapTrendsInput.model_validate({"variable": "air_temp", "box": box, **fields})


def context(source: FakeSource, public_base_url: str | None = None) -> ToolContext:
    return ToolContext(
        source=source, last_complete_year=LAST_COMPLETE_YEAR, public_base_url=public_base_url
    )


async def run_map(
    cells: Mapping[GridPoint, MonthlyValues], box: Box = BOX, **fields: Any
) -> TrendMap:
    return await map_trends(map_input(box, **fields), context(RegionalFakeSource(cells)))


def cell_at(trend_map: TrendMap, grid_point: GridPoint) -> MapCell:
    (cell,) = [cell for cell in trend_map.cells if (cell.lat, cell.lon) == grid_point]
    return cell


def seasonal(summer: dict[int, float], rest_of_year: dict[int, float]) -> dict[MonthKey, float]:
    """June to August from `summer`, every other month from `rest_of_year`."""
    return {
        (year, month): summer[year] if month in (6, 7, 8) else rest_of_year[year]
        for year in summer
        for month in range(1, 13)
    }


# The request (spec 7, step 1; spec 6, "How the app calls it")


async def test_box_is_fetched_once_for_the_variables_code_and_whole_record() -> None:
    source = RegionalFakeSource({STRONG_POINT: RISING})
    await map_trends(map_input(variable="precipitation"), context(source))
    assert source.regional_calls == [("PRECTOTCORR", BOX, LAST_COMPLETE_YEAR)]
    assert source.calls == []


async def test_period_is_clamped_to_the_record_and_the_last_complete_year() -> None:
    with pytest.raises(BadPeriodError, match="dates were not changed"):
        await run_map({STRONG_POINT: RISING}, **{"from": 1950, "to": 2100})


async def test_unknown_variable_raises_before_any_fetch() -> None:
    source = RegionalFakeSource({STRONG_POINT: RISING})
    with pytest.raises(UnknownVariableError):
        await map_trends(map_input(variable="T2M"), context(source))
    assert source.regional_calls == []


async def test_period_without_years_raises_bad_period_before_any_fetch() -> None:
    source = RegionalFakeSource({STRONG_POINT: RISING})
    with pytest.raises(BadPeriodError):
        await map_trends(map_input(**{"from": 2030}), context(source))
    assert source.regional_calls == []


# Box limits (spec 10)


@pytest.mark.parametrize(
    "box",
    [
        pytest.param(Box(south=55, west=20, north=65.5, east=22), id="too_tall"),
        pytest.param(Box(south=55, west=20, north=57, east=30.5), id="too_wide"),
        pytest.param(Box(south=55, west=20, north=56.9, east=22), id="too_short"),
        pytest.param(Box(south=55, west=20, north=57, east=21.9), id="too_narrow"),
        pytest.param(Box(south=55, west=20, north=56, east=21), id="one_degree"),
        pytest.param(Box(south=57, west=20, north=55, east=22), id="south_above_north"),
        pytest.param(Box(south=55, west=22, north=57, east=20), id="west_east_of_east"),
        pytest.param(Box(south=55, west=175, north=57, east=-175), id="crosses_antimeridian"),
        pytest.param(Box(south=55, west=20, north=55, east=22), id="no_height"),
        # POWER compares the plain float difference: 2.3 - 0.3 is just under 2 and
        # -63.98 - -73.98 just over 10, and it rejected both (13 November 2026).
        pytest.param(Box(south=0.3, west=20, north=2.3, east=22), id="float_just_under_two"),
        pytest.param(Box(south=20, west=-73.98, north=22, east=-63.98), id="float_just_over_ten"),
    ],
)
async def test_box_outside_the_limits_raises_bad_place_before_any_fetch(box: Box) -> None:
    source = RegionalFakeSource({STRONG_POINT: RISING})
    with pytest.raises(BadPlaceError):
        await map_trends(map_input(box), context(source))
    assert source.regional_calls == []


@pytest.mark.parametrize(
    "box",
    [
        pytest.param(Box(south=55, west=20, north=57, east=22), id="two_degrees"),
        pytest.param(Box(south=55, west=20, north=65, east=30), id="ten_degrees"),
        pytest.param(Box(south=-12.5, west=-60, north=-5, east=-55), id="southwest"),
    ],
)
async def test_box_within_the_limits_is_fetched(box: Box) -> None:
    source = RegionalFakeSource({STRONG_POINT: RISING})
    await map_trends(map_input(box), context(source))
    assert source.regional_calls == [("T2M", box, LAST_COMPLETE_YEAR)]


async def test_box_edges_are_rounded_to_two_decimals_before_the_fetch() -> None:
    source = RegionalFakeSource({STRONG_POINT: RISING})
    given = Box(south=-33.456, west=150.5, north=-31.4, east=152.504)
    trend_map = await map_trends(map_input(given), context(source))
    assert source.regional_calls == [("T2M", given, LAST_COMPLETE_YEAR)]
    assert trend_map.box == given


# Cells (spec 7, "Region view")


async def test_cells_hold_the_rate_per_decade_and_the_corrected_p_value() -> None:
    trend_map = await run_map({STRONG_POINT: RISING})
    cell = cell_at(trend_map, STRONG_POINT)
    assert cell.sen_slope == pytest.approx(0.5)
    assert cell.mk_p is None
    assert not cell.significant


async def test_cell_has_the_rate_and_p_value_of_the_case_it_opens() -> None:
    trend_map = await run_map({MODERATE_POINT: MODERATE})
    lat, lon = MODERATE_POINT
    case = await analyze_trend(
        AnalyzeTrendInput.model_validate(
            {"variable": "air_temp", "place": {"lat": lat, "lon": lon}}
        ),
        context(FakeSource(MODERATE)),
    )
    trend = case.results[0].trend
    assert trend is not None
    cell = cell_at(trend_map, MODERATE_POINT)
    assert cell.sen_slope == trend.sen_slope
    assert cell.mk_p is None
    assert trend.method_id == ("mk_mc_envelope_v1" if trend_map.variable.id == "air_temp" else None)


async def test_benjamini_hochberg_marks_only_cells_that_pass_the_stricter_rule() -> None:
    cells = {STRONG_POINT: RISING, MODERATE_POINT: MODERATE} | dict.fromkeys(OTHER_POINTS, FLAT)
    trend_map = await run_map(cells)
    moderate = cell_at(trend_map, MODERATE_POINT)
    assert not cell_at(trend_map, STRONG_POINT).significant
    assert moderate.mk_p is None
    assert not moderate.significant
    assert not any(cell_at(trend_map, point).significant for point in OTHER_POINTS)


async def test_cells_without_a_result_do_not_count_toward_the_correction() -> None:
    cells = {STRONG_POINT: RISING, MODERATE_POINT: MODERATE} | dict.fromkeys(OTHER_POINTS, SHORT)
    trend_map = await run_map(cells)
    assert not cell_at(trend_map, STRONG_POINT).significant
    assert not cell_at(trend_map, MODERATE_POINT).significant


@pytest.mark.parametrize("monthly", [SHORT, ALL_MISSING, {}], ids=["short", "missing", "empty"])
async def test_cell_with_too_few_years_has_no_result_and_is_not_significant(
    monthly: MonthlyValues,
) -> None:
    trend_map = await run_map({STRONG_POINT: RISING, MODERATE_POINT: monthly})
    assert cell_at(trend_map, MODERATE_POINT) == MapCell(
        lat=MODERATE_POINT[0], lon=MODERATE_POINT[1], sen_slope=None, mk_p=None, significant=False
    )


async def test_ten_years_are_enough_to_test_a_cell() -> None:
    trend_map = await run_map({STRONG_POINT: RISING}, **{"from": 2016})
    assert cell_at(trend_map, STRONG_POINT).sen_slope == pytest.approx(0.5)


async def test_cells_use_the_requested_season() -> None:
    warming_summers = seasonal(line(0.05), line(-0.05))
    summer = await run_map({STRONG_POINT: warming_summers}, season="JJA")
    annual = await run_map({STRONG_POINT: warming_summers})
    assert cell_at(summer, STRONG_POINT).sen_slope == pytest.approx(0.5)
    assert cell_at(annual, STRONG_POINT).sen_slope == pytest.approx(-0.2479452055)


async def test_cells_are_ordered_by_latitude_then_longitude() -> None:
    points = row(3, lat=56.0) + row(3, lat=55.5)
    trend_map = await run_map(dict.fromkeys(reversed(points), RISING))
    assert [(cell.lat, cell.lon) for cell in trend_map.cells] == sorted(points)


# A map cell opened as a case (spec 6, "Caching"; spec 7, "Region view")

# Spec 6, "Limits we observed": POWER answered a 2° box from 59° to 61° N and 24° to 26° E with
# four 1° cells of sunlight or cloud, at their centres.
ONE_DEGREE_BOX = Box(south=59.0, west=24.0, north=61.0, east=26.0)
ONE_DEGREE_CELLS = [(59.5, 24.5), (59.5, 25.5), (60.5, 24.5), (60.5, 25.5)]
OPENED_CELL = (60.5, 24.5)


def power_values(monthly: MonthlyValues) -> dict[str, float | None]:
    """Monthly values keyed as POWER sends them, "YYYYMM"."""
    return {f"{year:04d}{month:02d}": value for (year, month), value in monthly.items()}


class OneDegreePower:
    """Stands in for POWER: answers a regional call with `cells` for its code, and a point call
    with FLAT for every code it asks for. Records every request.
    """

    def __init__(self, cells: Mapping[GridPoint, MonthlyValues]) -> None:
        self.requests: list[httpx.Request] = []
        self._cells = cells

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        codes = request.url.params["parameters"].split(",")
        header = {"api": {"version": FAKE_VERSION}, "fill_value": -999.0}
        if request.url.path == REGIONAL_PATH:
            (code,) = codes
            features = [
                {
                    "geometry": {"type": "Point", "coordinates": [lon, lat, 0.0]},
                    "properties": {"parameter": {code: power_values(monthly)}},
                }
                for (lat, lon), monthly in self._cells.items()
            ]
            return httpx.Response(200, json={"header": header, "features": features})
        parameter = {code: power_values(FLAT) for code in codes}
        return httpx.Response(200, json={"header": header, "properties": {"parameter": parameter}})


async def open_cloud_map_cell(
    tmp_path: Path,
) -> tuple[MapCell, Investigation, list[httpx.Request]]:
    """Map cloud cover over ONE_DEGREE_BOX, then open OPENED_CELL as a case at its centre,
    through the real POWER client and cache. Returns the cell, the case and POWER's requests.
    """
    cells = dict.fromkeys(ONE_DEGREE_CELLS, RISING) | {OPENED_CELL: MODERATE}
    power = OneDegreePower(cells)
    cache = Cache(tmp_path / "cache.sqlite")
    client = PowerClient(
        cache,
        httpx.AsyncClient(transport=httpx.MockTransport(power)),
        today=lambda: date(2026, 11, 13),
    )
    try:
        ctx = ToolContext(source=client, last_complete_year=LAST_COMPLETE_YEAR)
        trend_map = await map_trends(map_input(ONE_DEGREE_BOX, variable="cloud_cover"), ctx)
        cell = cell_at(trend_map, OPENED_CELL)
        case = await analyze_trend(
            AnalyzeTrendInput.model_validate(
                {"variable": "cloud_cover", "place": {"lat": cell.lat, "lon": cell.lon}}
            ),
            ctx,
        )
    finally:
        await client.aclose()
        cache.close()
    return cell, case, power.requests


async def test_case_opened_at_a_one_degree_map_cell_reads_the_values_the_map_cached(
    tmp_path: Path,
) -> None:
    cell, case, _ = await open_cloud_map_cell(tmp_path)

    trend = case.results[0].trend
    assert trend is not None
    assert (case.results[0].place.cell.lat, case.results[0].place.cell.lon) == OPENED_CELL
    assert cell.sen_slope == trend.sen_slope
    assert cell.mk_p is None
    assert trend.method_id is None


async def test_case_opened_at_a_one_degree_map_cell_asks_only_for_the_other_one_degree_codes(
    tmp_path: Path,
) -> None:
    _, _, requests = await open_cloud_map_cell(tmp_path)

    point_requests = [request for request in requests if request.url.path == POINT_PATH]
    assert [
        (
            request.url.params["latitude"],
            request.url.params["longitude"],
            request.url.params["parameters"],
        )
        for request in point_requests
    ] == [("60.5", "24.5", "ALLSKY_SFC_SW_DWN,AOD_55_ADJ")]


# Area mean (spec 7, "Region view")


async def test_area_mean_weights_each_cell_by_the_cosine_of_its_latitude() -> None:
    box = Box(south=50.0, west=20.0, north=60.0, east=25.0)
    cells = {
        (50.0, 20.0): monthly_from_yearly(dict.fromkeys(RECORD_YEARS, 10.0)),
        (60.0, 20.0): monthly_from_yearly(dict.fromkeys(RECORD_YEARS, 40.0)),
    }
    trend_map = await run_map(cells, box)
    w50, w60 = math.cos(math.radians(50.0)), math.cos(math.radians(60.0))
    expected = (10.0 * w50 + 40.0 * w60) / (w50 + w60)
    assert [value.value for value in trend_map.area_mean.series] == pytest.approx(
        [expected] * len(RECORD_YEARS)
    )


async def test_area_mean_rate_is_the_weighted_mean_of_the_cells_rates() -> None:
    box = Box(south=50.0, west=20.0, north=60.0, east=25.0)
    cells = {
        (50.0, 20.0): monthly_from_yearly(line(0.03)),
        (60.0, 20.0): monthly_from_yearly(line(0.06)),
    }
    trend_map = await run_map(cells, box)
    w50, w60 = math.cos(math.radians(50.0)), math.cos(math.radians(60.0))
    expected_per_decade = 10 * (0.03 * w50 + 0.06 * w60) / (w50 + w60)
    assert trend_map.area_mean.trend is not None
    assert trend_map.area_mean.trend.sen_slope == pytest.approx(expected_per_decade)


async def test_area_mean_leaves_out_a_cell_missing_a_month() -> None:
    box = Box(south=50.0, west=20.0, north=60.0, east=25.0)
    gappy = monthly_from_yearly(dict.fromkeys(RECORD_YEARS, 40.0))
    gappy[(2000, 6)] = None
    cells = {
        (50.0, 20.0): monthly_from_yearly(dict.fromkeys(RECORD_YEARS, 10.0)),
        (60.0, 20.0): gappy,
    }
    trend_map = await run_map(cells, box)
    # June 2000 is the 50° cell's value alone; the other eleven months average both cells.
    (year_2000,) = [value for value in trend_map.area_mean.series if value.year == 2000]
    assert year_2000.value is None


async def test_area_mean_is_analysed_exactly_like_a_place() -> None:
    cells = {(55.0, 20.0): RISING, (65.0, 30.0): MODERATE, (60.0, 25.0): FLAT}
    trend_map = await run_map(cells)
    weighted = cos_lat_weighted_mean([(lat, monthly) for (lat, _), monthly in cells.items()])
    case = await analyze_trend(
        AnalyzeTrendInput.model_validate(
            {"variable": "air_temp", "place": {"lat": 60.0, "lon": 25.0, "name": AREA_MEAN_NAME}}
        ),
        context(FakeSource(weighted)),
    )
    place_result = case.results[0]
    area_mean = trend_map.area_mean
    assert area_mean.trend is not None
    assert area_mean.series == place_result.series
    assert area_mean.trend.sen_slope == place_result.trend.sen_slope
    assert area_mean.trend.mk_p is None
    assert area_mean.verdict.kind == "inference_unavailable"
    assert area_mean.verdict.kind == "inference_unavailable"


async def test_area_mean_sits_at_the_box_centre_with_the_box_as_its_cell() -> None:
    trend_map = await run_map({STRONG_POINT: RISING})
    place = trend_map.area_mean.place
    assert place.name == AREA_MEAN_NAME
    assert (place.lat, place.lon) == (60.0, 25.0)
    assert place.cell.model_dump() == {"lat": 60.0, "lon": 25.0, "height": 10.0, "width": 10.0}


async def test_area_mean_sentence_names_the_selected_area() -> None:
    trend_map = await run_map({STRONG_POINT: RISING})
    assert "the selected area" in trend_map.area_mean.verdict.sentence
    assert "Significance has not been assessed" in trend_map.area_mean.verdict.sentence


async def test_area_mean_step_starts_with_a_capital_letter() -> None:
    steps = (await run_map({STRONG_POINT: RISING})).steps
    assert steps[-1].startswith("The selected area: 45 complete years from 1981 to 2025.")


async def test_area_mean_point_and_cell_carry_no_floating_point_error() -> None:
    box = Box(south=55.1, west=20.0, north=65.1, east=22.5)
    place = (await run_map({STRONG_POINT: RISING}, box)).area_mean.place
    assert (place.lat, place.lon) == (60.1, 21.25)
    assert (place.cell.height, place.cell.width) == (10.0, 2.5)


async def test_ocean_box_gives_no_data_for_every_cell_and_the_area_mean() -> None:
    trend_map = await run_map(dict.fromkeys(row(4), ALL_MISSING), variable="surface_soil_wetness")
    assert all(cell.mk_p is None and not cell.significant for cell in trend_map.cells)
    assert trend_map.area_mean.trend is None
    assert trend_map.area_mean.verdict.kind == "no_data"


# Links, sources, steps and determinism


async def test_app_url_holds_the_map_parameters_in_spec_order() -> None:
    source = RegionalFakeSource({STRONG_POINT: RISING})
    inp = map_input(**{"from": 1990, "to": 2020, "season": "JJA"})
    trend_map = await map_trends(inp, context(source, BASE_URL))
    assert trend_map.app_url == f"{BASE_URL}/map?v=air_temp&from=1990&to=2020&s=JJA&box=55,20,65,30"


async def test_app_url_is_a_path_without_a_public_base_url() -> None:
    trend_map = await run_map({STRONG_POINT: RISING})
    assert trend_map.app_url == "/map?v=air_temp&from=1981&to=2025&s=annual&box=55,20,65,30"


async def test_app_url_writes_box_edges_with_two_decimals_and_no_trailing_zeros() -> None:
    box = Box(south=-33.456, west=150.5, north=-31.4, east=152.504)
    trend_map = await run_map({STRONG_POINT: RISING}, box)
    assert trend_map.app_url.endswith("&box=-33.456,150.5,-31.4,152.504")


async def test_cells_from_one_source_list_it_once() -> None:
    trend_map = await run_map(dict.fromkeys(row(5), RISING))
    entry = get_entry("air_temp")
    assert trend_map.sources == [
        SourceRef(name=entry.source, version=FAKE_VERSION, accessed=FAKE_ACCESSED)
    ]


async def test_steps_report_how_many_cells_were_tested_and_marked() -> None:
    cells = (
        {STRONG_POINT: RISING, MODERATE_POINT: MODERATE}
        | dict.fromkeys(OTHER_POINTS, FLAT)
        | {(64.0, 20.0): SHORT}
    )
    steps = (await run_map(cells)).steps
    assert "descriptive rates for 13 grid points" in " ".join(steps)
    assert "Significance is not assessed" in " ".join(steps)


async def test_same_inputs_give_the_same_map_whatever_order_the_source_returns() -> None:
    cells = {STRONG_POINT: RISING, MODERATE_POINT: MODERATE} | dict.fromkeys(OTHER_POINTS, FLAT)
    reordered = dict(reversed(list(cells.items())))
    first = await run_map(cells)
    again = await run_map(cells)
    reversed_map = await run_map(reordered)
    assert first.model_dump() == again.model_dump() == reversed_map.model_dump()
