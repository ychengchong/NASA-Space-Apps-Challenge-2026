"""analyze_trend and compare_places, one case as one Investigation, and map_trends, the trends of
every grid cell in a box as one TrendMap (spec 5; spec 7, "Method" and "Region view").
"""

import asyncio
import hashlib
from collections.abc import Sequence
from urllib.parse import quote, urlencode

from app.catalogue import CatalogueEntry, GridAlignment, get_entry, to_summary
from app.errors import BadPlaceError
from app.models import (
    AnalyzeTrendInput,
    Box,
    Cell,
    ComparePlacesInput,
    Contrast,
    Investigation,
    MapCell,
    MapTrendsInput,
    Place,
    PlaceInput,
    PlaceResult,
    Requested,
    Season,
    SourceRef,
    Trend,
    TrendMap,
    YearValue,
)
from app.sources.base import MonthlyValues, PointSeries
from app.stats import (
    FALSE_DISCOVERY_RATE,
    MIN_YEARS_FOR_TEST,
    benjamini_hochberg,
    compute_trend,
    cos_lat_weighted_mean,
    period_scan,
    to_trend,
    yearly_values,
)
from app.tools.context import ToolContext
from app.tools.places import (
    LINK_COORDINATE_DECIMALS,
    format_coordinates,
    resolve_place,
    round_link_coordinate,
)
from app.tools.series import fetch_point_series, resolve_period
from app.verdict import build_verdict, compare_places_summary

# Spec 5: the id is a short hash of the normalised inputs; this many hex digits of SHA-256.
CASE_ID_HEX_DIGITS = 12
# Spec 10: the web app's page for a case.
CASE_PATH = "/case"
# Spec 10: the web app's page for a trend map.
MAP_PATH = "/map"
# Spec 5 and spec 7, "Region view": the area mean is analysed like a place with this name. It is
# lower case because it stands inside the verdict sentence: "Air temperature in the selected
# area has risen by about ...".
AREA_MEAN_NAME = "the selected area"
# Spec 6, "Limits we observed", and spec 10: each side of a box may be from 2° to 10°. Checked
# live on 13 November 2026: POWER's regional endpoint answered HTTP 422 for sides of 1° and
# 1.9° ("Please provide at least a 2 degree range") and of 10.5° ("Please provide a maximum of
# 10 degree range"), and accepted sides of exactly 2°, 3°, 5° and 10°. It compares the plain
# floating-point difference of the edges: 0.3 to 2.3 (1.9999999999999998) was rejected as under
# 2°, and -73.98 to -63.98 (10.000000000000007) as over 10°, so the check here does the same.
MIN_BOX_SIDE_DEGREES = 2.0
MAX_BOX_SIDE_DEGREES = 10.0
# Box edges carry the link's two decimals (spec 11), so the box's centre has at most one more.
# Rounding to these removes only floating-point error from the area mean's point and cell.
BOX_CENTRE_DECIMALS = LINK_COORDINATE_DECIMALS + 1
BOX_SIDE_DECIMALS = LINK_COORDINATE_DECIMALS
# Spec 5, "Inputs": the months each season names.
SEASON_DESCRIPTIONS: dict[Season, str] = {
    "annual": "the twelve months",
    "DJF": "December to February",
    "MAM": "March to May",
    "JJA": "June to August",
    "SON": "September to November",
}


async def analyze_trend(inp: AnalyzeTrendInput, ctx: ToolContext) -> Investigation:
    """The trend of one variable at one place, as an Investigation with one result.

    Follows spec 7, "Method": yearly values for the clamped period and season, the corrected
    Mann-Kendall test with Sen's slope per decade, and the verdict. Years with a missing month
    stay in the series as None and are left out of the test. Fewer than 10 yearly values give
    the verdict kind "too_few_years", and none at all "no_data"; both have no trend. Raises
    `UnknownVariableError`, `BadPeriodError` or `SourceUnavailableError`.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    results, sources = await _analyse_places(entry, [inp.place], requested, inp.scan, ctx)
    return _investigation(entry, [inp.place], requested, results, sources, ctx)


async def compare_places(inp: ComparePlacesInput, ctx: ToolContext) -> Investigation:
    """The trend of one variable at two to four places over the same years.

    Each place is analysed exactly as `analyze_trend` would, and the results keep the order of
    the places. The contrast and the summary sentence follow spec 7, "Comparing places". The
    places are fetched at the same time. Raises the same errors as `analyze_trend`.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    results, sources = await _analyse_places(entry, inp.places, requested, inp.scan, ctx)
    contrast, summary = compare_places_summary(entry, results)
    return _investigation(
        entry, inp.places, requested, results, sources, ctx, contrast=contrast, summary=summary
    )


async def _analyse_places(
    entry: CatalogueEntry,
    place_inputs: Sequence[PlaceInput],
    requested: Requested,
    scan: bool,
    ctx: ToolContext,
) -> tuple[list[PlaceResult], list[SourceRef]]:
    places = [resolve_place(place_input, entry) for place_input in place_inputs]
    # gather, not a TaskGroup, so a failed fetch raises its own AppError for the adapters.
    point_series = await asyncio.gather(
        *(fetch_point_series(entry, place, ctx) for place in places)
    )
    results = [
        _place_result(entry, place, series.monthly, requested, scan)
        for place, series in zip(places, point_series, strict=True)
    ]
    return results, _sources(entry, point_series)


def _place_result(
    entry: CatalogueEntry,
    place: Place,
    monthly: MonthlyValues,
    requested: Requested,
    scan: bool,
) -> PlaceResult:
    yearly = yearly_values(monthly, requested.season, requested.from_, requested.to)
    years, values = _years_with_values(yearly)
    trend = _trend(years, values, scan)
    return PlaceResult(
        place=place,
        series=[YearValue(year=year, value=value) for year, value in yearly],
        trend=trend,
        verdict=build_verdict(entry, place.name, len(values), trend),
    )


def _years_with_values(yearly: Sequence[tuple[int, float | None]]) -> tuple[list[int], list[float]]:
    """The years that have a value, and those values: what the trend test runs on."""
    years = [year for year, value in yearly if value is not None]
    values = [value for _, value in yearly if value is not None]
    return years, values


def _trend(years: list[int], values: list[float], scan: bool) -> Trend | None:
    # Spec 7, step 3: too few yearly values to test, so no trend at all.
    if len(values) < MIN_YEARS_FOR_TEST:
        return None
    scan_points = period_scan(years, values) if scan else None
    return to_trend(compute_trend(years, values), scan_points)


def _sources(entry: CatalogueEntry, point_series: Sequence[PointSeries]) -> list[SourceRef]:
    sources: list[SourceRef] = []
    for series in point_series:
        source = SourceRef(name=entry.source, version=series.version, accessed=series.accessed)
        if source not in sources:
            sources.append(source)
    return sources


def _investigation(
    entry: CatalogueEntry,
    place_inputs: Sequence[PlaceInput],
    requested: Requested,
    results: list[PlaceResult],
    sources: list[SourceRef],
    ctx: ToolContext,
    contrast: Contrast | None = None,
    summary: str | None = None,
) -> Investigation:
    query = _case_query(entry.id, place_inputs, requested)
    return Investigation(
        id=hashlib.sha256(query.encode("utf-8")).hexdigest()[:CASE_ID_HEX_DIGITS],
        variable=to_summary(entry),
        requested=requested,
        results=results,
        contrast=contrast,
        summary=summary,
        steps=_steps(entry, place_inputs, requested, results),
        sources=sources,
        app_url=f"{ctx.public_base_url or ''}{CASE_PATH}?{query}",
    )


def _case_query(variable_id: str, place_inputs: Sequence[PlaceInput], requested: Requested) -> str:
    """The case parameters of spec 10 in their order: v, p..., label..., from, to, s.

    Coordinates are rounded to two decimals (spec 11). Labels appear only when some place has
    one, and then once per place, empty for a place without one, so they stay in step with p.
    The scan is a display option and not part of the case.
    """
    labels = [_label(place_input) for place_input in place_inputs]
    params = [("v", variable_id)]
    params += [("p", _link_point(place_input)) for place_input in place_inputs]
    if any(labels):
        params += [("label", label) for label in labels]
    params += [("from", str(requested.from_)), ("to", str(requested.to)), ("s", requested.season)]
    return urlencode(params, safe=",", quote_via=quote)


def _label(place_input: PlaceInput) -> str:
    # The same rule as resolve_place: a blank name is no name.
    return place_input.name.strip() if place_input.name else ""


def _link_point(place_input: PlaceInput) -> str:
    return f"{_link_coordinate(place_input.lat)},{_link_coordinate(place_input.lon)}"


def _link_coordinate(x: float) -> str:
    """Two decimals at most, without trailing zeros: 60.17, 60.1 or 60."""
    return f"{round_link_coordinate(x):.2f}".rstrip("0").rstrip(".")


def _steps(
    entry: CatalogueEntry,
    place_inputs: Sequence[PlaceInput],
    requested: Requested,
    results: Sequence[PlaceResult],
) -> list[str]:
    """What the tool layer did, in plain words. It depends only on the inputs and the results,
    so it reads the same whether the values came from the cache or from NASA POWER.
    """
    steps = [_variable_step(entry)]
    steps += [
        _grid_step(entry, place_input, result.place)
        for place_input, result in zip(place_inputs, results, strict=True)
    ]
    steps.append(_period_step(requested))
    steps += [_test_step(result) for result in results]
    return steps


def _variable_step(entry: CatalogueEntry) -> str:
    return f"Chose the variable {entry.name} ({entry.id}), with monthly values from {entry.source}."


def _grid_step(entry: CatalogueEntry, place_input: PlaceInput, place: Place) -> str:
    point = f"{_link_coordinate(place_input.lat)}, {_link_coordinate(place_input.lon)}"
    label = _label(place_input)
    requested_point = f"{label} ({point})" if label else point
    cell = place.cell
    centre = format_coordinates(cell.lat, cell.lon)
    if entry.grid.alignment is GridAlignment.BOUNDED_BY_MULTIPLES:
        return (
            f"Used the {cell.height:g}° by {cell.width:g}° cell that holds {requested_point}, "
            f"centred on {centre}."
        )
    return (
        f"Used the grid point nearest to {requested_point}: {centre}, "
        f"in a cell of {cell.height:g}° by {cell.width:g}°."
    )


def _period_step(requested: Requested) -> str:
    step = (
        f"Averaged {SEASON_DESCRIPTIONS[requested.season]} of each year from {requested.from_} "
        f"to {requested.to} into one value per year. A year with a missing month has no value."
    )
    if requested.season == "DJF":
        step += " December counts toward the following year."
    return step


def _test_step(result: PlaceResult) -> str:
    name = result.place.name
    complete_years = sum(1 for year_value in result.series if year_value.value is not None)
    trend = result.trend
    if complete_years == 0:
        return f"{name}: no year in the period has a value for every month, so no test was run."
    if trend is None:
        years = "1 complete year" if complete_years == 1 else f"{complete_years} complete years"
        return (
            f"{name}: {years}, fewer than the {MIN_YEARS_FOR_TEST} a trend test needs, "
            "so no test was run."
        )
    step = (
        f"{name}: {trend.n} complete years from {trend.first_year} to {trend.last_year}. "
        "Ran the Mann-Kendall test with Sen's slope and a least-squares cross-check. "
        f"{_correction_text(trend)}"
    )
    if trend.scan is not None:
        step += (
            f" Repeated the test from each of {len(trend.scan)} start years that leave at least "
            f"{MIN_YEARS_FOR_TEST} years."
        )
    return step


def _correction_text(trend: Trend) -> str:
    # Spec 7, step 5: the correction applies only when r1 is positive.
    if trend.lag1 > 0:
        return (
            f"The lag-1 autocorrelation of {trend.lag1:.2f} gave a correction factor of "
            f"{trend.variance_factor:.2f} for year-to-year memory."
        )
    return "The lag-1 autocorrelation was not positive, so the correction factor was 1."


async def map_trends(inp: MapTrendsInput, ctx: ToolContext) -> TrendMap:
    """The trend of one variable at every grid cell in a box, and of their area mean.

    Follows spec 7, "Region view". The box's edges are first rounded to two decimals, as in a
    link, so a shared map reopens the same cells; the result reports that box. Its south edge
    must lie below its north edge and its west edge west of its east edge, so it never crosses
    the 180° meridian, and each side must be from 2° to 10°. Otherwise `BadPlaceError` is
    raised before any data is fetched.

    Each grid point the source returns for the box is tested as a place would be, on the yearly
    values of the clamped period and season, giving Sen's slope per decade and the corrected
    Mann-Kendall p-value. A cell with fewer than 10 yearly values, or none, has None for both
    and is never significant. `significant` is the Benjamini-Hochberg correction at a 5% false
    discovery rate over the p-values of the cells that have one. Cells are ordered by latitude,
    then longitude.

    The area mean weights each cell's monthly values by the cosine of its latitude, leaving out
    missing values, and is analysed exactly as `analyze_trend` analyses a place: it is named
    "the selected area", sits at the box's centre, and its cell is the box. Raises
    `UnknownVariableError`, `BadPeriodError`, `BadPlaceError` or `SourceUnavailableError`.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    box = _link_box(inp.box)
    _check_box(box)
    found = await ctx.source.regional_series(entry.code, box, ctx.last_complete_year)
    grid_points = sorted(found)
    point_series = [found[grid_point] for grid_point in grid_points]
    trends = [_cell_trend(series.monthly, requested) for series in point_series]
    area_monthly = cos_lat_weighted_mean(
        [(lat, series.monthly) for (lat, _), series in zip(grid_points, point_series, strict=True)]
    )
    area_mean = _place_result(entry, _area_place(box), area_monthly, requested, scan=False)
    cells = _map_cells(grid_points, trends)
    return TrendMap(
        variable=to_summary(entry),
        requested=requested,
        box=box,
        cells=cells,
        area_mean=area_mean,
        steps=_map_steps(entry, box, requested, cells, area_mean),
        sources=_sources(entry, point_series),
        app_url=f"{ctx.public_base_url or ''}{MAP_PATH}?{_map_query(entry.id, box, requested)}",
    )


def _link_box(box: Box) -> Box:
    """The box with each edge rounded as in a link (spec 11)."""
    return Box(
        south=round_link_coordinate(box.south),
        west=round_link_coordinate(box.west),
        north=round_link_coordinate(box.north),
        east=round_link_coordinate(box.east),
    )


def _check_box(box: Box) -> None:
    if box.south >= box.north or box.west >= box.east:
        raise BadPlaceError(
            "Give the box as south,west,north,east, with its south edge below its north edge "
            "and its west edge west of its east edge. A box cannot cross the 180° meridian."
        )
    # Plain differences, compared as POWER compares them (see MIN_BOX_SIDE_DEGREES).
    sides = (box.north - box.south, box.east - box.west)
    if not all(MIN_BOX_SIDE_DEGREES <= side <= MAX_BOX_SIDE_DEGREES for side in sides):
        raise BadPlaceError(
            f"Each side of the box must be from {MIN_BOX_SIDE_DEGREES:g}° "
            f"to {MAX_BOX_SIDE_DEGREES:g}°."
        )


def _cell_trend(monthly: MonthlyValues, requested: Requested) -> Trend | None:
    """One cell's trend, as `_place_result` computes it for a place; None with too few years."""
    yearly = yearly_values(monthly, requested.season, requested.from_, requested.to)
    years, values = _years_with_values(yearly)
    return _trend(years, values, scan=False)


def _map_cells(
    grid_points: Sequence[tuple[float, float]], trends: Sequence[Trend | None]
) -> list[MapCell]:
    # Spec 7, "Region view": the correction runs on the final p-values of the cells that have a
    # result, so a cell without one neither counts toward it nor passes it.
    tested = {
        grid_point: trend
        for grid_point, trend in zip(grid_points, trends, strict=True)
        if trend is not None
    }
    passes = benjamini_hochberg([trend.mk_p for trend in tested.values()], FALSE_DISCOVERY_RATE)
    significant = dict(zip(tested, passes, strict=True))
    return [
        MapCell(
            lat=lat,
            lon=lon,
            sen_slope=trend.sen_slope if trend is not None else None,
            mk_p=trend.mk_p if trend is not None else None,
            significant=significant.get((lat, lon), False),
        )
        for (lat, lon), trend in zip(grid_points, trends, strict=True)
    ]


def _area_place(box: Box) -> Place:
    centre_lat = round((box.south + box.north) / 2, BOX_CENTRE_DECIMALS)
    centre_lon = round((box.west + box.east) / 2, BOX_CENTRE_DECIMALS)
    return Place(
        name=AREA_MEAN_NAME,
        lat=centre_lat,
        lon=centre_lon,
        cell=Cell(
            lat=centre_lat,
            lon=centre_lon,
            height=round(box.north - box.south, BOX_SIDE_DECIMALS),
            width=round(box.east - box.west, BOX_SIDE_DECIMALS),
        ),
    )


def _map_query(variable_id: str, box: Box, requested: Requested) -> str:
    """The map parameters of spec 10 in their order: v, from, to, s, box=south,west,north,east."""
    edges = (box.south, box.west, box.north, box.east)
    params = [
        ("v", variable_id),
        ("from", str(requested.from_)),
        ("to", str(requested.to)),
        ("s", requested.season),
        ("box", ",".join(_link_coordinate(edge) for edge in edges)),
    ]
    return urlencode(params, safe=",", quote_via=quote)


def _map_steps(
    entry: CatalogueEntry,
    box: Box,
    requested: Requested,
    cells: Sequence[MapCell],
    area_mean: PlaceResult,
) -> list[str]:
    """What map_trends did, in plain words. Like `_steps`, it depends only on the inputs and
    the results.
    """
    tested = sum(1 for cell in cells if cell.mk_p is not None)
    steps = [
        _variable_step(entry),
        (
            f"Used the {_count(len(cells), 'grid point')} inside the box from "
            f"{_edge(box.south, 'N', 'S')} to {_edge(box.north, 'N', 'S')} and from "
            f"{_edge(box.west, 'E', 'W')} to {_edge(box.east, 'E', 'W')}."
        ),
        _period_step(requested),
        (
            f"Tested {tested} of {_count(len(cells), 'grid point')} with the Mann-Kendall test "
            f"and Sen's slope, corrected for year-to-year memory. A grid point needs at least "
            f"{MIN_YEARS_FOR_TEST} complete years to be tested."
        ),
    ]
    if tested > 0:
        marked = sum(1 for cell in cells if cell.significant)
        steps.append(
            f"Marked {marked} of {_count(tested, 'tested grid point')} as significant after a "
            f"Benjamini-Hochberg correction at a {FALSE_DISCOVERY_RATE:.0%} false discovery "
            "rate, a stricter test because a map tests many grid points at once."
        )
    steps.append(
        "Averaged the grid points into one value per month, weighting each by the cosine of its "
        "latitude because grid cells shrink toward the poles, and analysed that area mean like "
        "a place."
    )
    steps.append(_capitalised(_test_step(area_mean)))
    return steps


def _capitalised(text: str) -> str:
    """`text` with its first letter in upper case, for a step that opens with AREA_MEAN_NAME."""
    return text[:1].upper() + text[1:]


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _edge(value: float, positive: str, negative: str) -> str:
    """A box edge as text with the link's decimals, such as "55°N" or "33.46°S"."""
    hemisphere = negative if value < 0 else positive
    return f"{_link_coordinate(abs(value))}°{hemisphere}"
