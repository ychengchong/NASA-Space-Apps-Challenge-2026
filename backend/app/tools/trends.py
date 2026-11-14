"""analyze_trend and compare_places, one case as one Investigation, and map_trends, the trends of
every grid cell in a box as one TrendMap (spec 5; spec 7, "Method" and "Region view").
"""

import asyncio
import hashlib
import json
from collections.abc import Sequence
from urllib.parse import quote, urlencode

from app.catalogue import CatalogueEntry, GridAlignment, get_entry, to_summary
from app.errors import BadPlaceError, BadRequestError
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
    ScanPoint,
    Season,
    SourceRef,
    Trend,
    TrendMap,
    Verdict,
    YearValue,
)
from app.sources.base import MonthlyValues, PointSeries
from app.stats import (
    FALSE_DISCOVERY_RATE,
    MIN_YEARS_FOR_TEST,
    benjamini_hochberg,
    cos_lat_weighted_mean,
    yearly_values,
)
from app.tools.context import ToolContext
from app.tools.inference import ANALYSIS_VERSION, analyse_values
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

    Annual values are day-weighted. Rates use real years and inference requires
    a complete requested annual T2M period, a homogeneous source and approved tables.
    Missing years remain gaps; unsupported inference is explicit and nullable.
    Fewer than ten values gives no rate. The result freezes evidence and an analysis version.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    results, sources = await _analyse_places(
        entry, [inp.place], requested, inp.scan, ctx, inp.snapshot_ids
    )
    return _investigation(entry, [inp.place], requested, results, sources, ctx)


async def compare_places(inp: ComparePlacesInput, ctx: ToolContext) -> Investigation:
    """The trend of one variable at two to four places over the same years.

    Each place is analysed exactly as `analyze_trend` would, and the results keep the order of
    the places. The contrast and the summary sentence follow spec 7, "Comparing places". The
    places are fetched at the same time. Raises the same errors as `analyze_trend`.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    results, sources = await _analyse_places(
        entry, inp.places, requested, inp.scan, ctx, inp.snapshot_ids
    )
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
    snapshot_ids: Sequence[str] = (),
) -> tuple[list[PlaceResult], list[SourceRef]]:
    if snapshot_ids and len(snapshot_ids) != len(place_inputs):
        raise BadRequestError("Give exactly one snapshot for each place.")
    places = [resolve_place(place_input, entry) for place_input in place_inputs]
    # gather, not a TaskGroup, so a failed fetch raises its own AppError for the adapters.
    point_series = await asyncio.gather(
        *(
            fetch_point_series(entry, place, ctx, snapshot_ids[index] if snapshot_ids else None)
            for index, place in enumerate(places)
        )
    )
    frozen = [ctx.snapshots.freeze(series) for series in point_series]
    common = None
    if len(places) > 1:
        available = [
            set(
                year
                for year, value in yearly_values(
                    series.monthly, requested.season, requested.from_, requested.to
                )
                if value is not None
            )
            for series in point_series
        ]
        common = set.intersection(*available)
    results = [
        _place_result(entry, place, series.monthly, requested, scan, common).model_copy(
            update={"snapshot_id": identity}
        )
        for place, series, identity in zip(places, point_series, frozen, strict=True)
    ]
    return results, _sources(entry, point_series, frozen)


def _place_result(
    entry: CatalogueEntry,
    place: Place,
    monthly: MonthlyValues,
    requested: Requested,
    scan: bool,
    common_years: set[int] | None = None,
    allow_inference: bool = True,
) -> PlaceResult:
    yearly = yearly_values(monthly, requested.season, requested.from_, requested.to)
    years, values = _years_with_values(yearly)
    if common_years is not None:
        selected = [
            (year, value) for year, value in zip(years, values, strict=True) if year in common_years
        ]
        years = [year for year, _ in selected]
        values = [value for _, value in selected]
    trend = analyse_values(
        years,
        values,
        entry,
        requested.season,
        allow_inference=allow_inference,
        complete_period=len(years) == requested.to - requested.from_ + 1,
    )
    if scan and trend is not None:
        trend.scan = [
            ScanPoint(start=years[index], sen_slope=tail.sen_slope, mk_p=None)
            for index in range(max(0, len(years) - MIN_YEARS_FOR_TEST + 1))
            if (
                tail := analyse_values(
                    years[index:], values[index:], entry, requested.season, allow_inference=False
                )
            )
            is not None
        ]
    verdict = build_verdict(entry, place.name, len(values), trend)
    if common_years is not None and not years and any(value is not None for _, value in yearly):
        verdict = Verdict(
            kind="inference_unavailable",
            direction=None,
            cautions=[],
            sentence="No common complete years are available for this comparison.",
        )
    return PlaceResult(
        place=place,
        series=[YearValue(year=year, value=value) for year, value in yearly],
        trend=trend,
        verdict=verdict,
        analysis_years=years,
    )


def _years_with_values(yearly: Sequence[tuple[int, float | None]]) -> tuple[list[int], list[float]]:
    """The years that have a value, and those values: what the trend test runs on."""
    years = [year for year, value in yearly if value is not None]
    values = [value for _, value in yearly if value is not None]
    return years, values


def _sources(
    entry: CatalogueEntry, point_series: Sequence[PointSeries], identities: Sequence[str] = ()
) -> list[SourceRef]:
    sources: list[SourceRef] = []
    for index, series in enumerate(point_series):
        source = SourceRef(
            name=entry.source,
            version=series.version,
            accessed=series.accessed,
            snapshot_id=identities[index] if identities else None,
            raw_sha256=series.raw_sha256,
            url=series.query_url or "https://power.larc.nasa.gov/",
            product=series.product or "Product release not recorded in legacy cache",
            provenance_status="raw_response_retained"
            if series.raw_sha256
            else "legacy_normalized_cache",
        )
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
    identities = [result.snapshot_id for result in results]
    params = [("snap", identity) for identity in identities if identity is not None]
    query += "&" + urlencode([*params, ("av", ANALYSIS_VERSION)])
    normalized = [result.model_dump(mode="json") for result in results]
    for result in normalized:
        if result["trend"] is not None:
            result["trend"].pop("scan", None)
    evidence = {"query": query, "results": normalized}
    return Investigation(
        id=hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        variable=to_summary(entry),
        requested=requested,
        results=results,
        contrast=contrast,
        summary=summary,
        steps=_steps(entry, place_inputs, requested, results),
        sources=sources,
        app_url=f"{ctx.public_base_url or ''}{CASE_PATH}?{query}",
        analysis_version=ANALYSIS_VERSION,
        common_years=results[0].analysis_years if len(results) > 1 else None,
        pinned=all(identity is not None for identity in identities),
    )


def _case_query(variable_id: str, place_inputs: Sequence[PlaceInput], requested: Requested) -> str:
    """The case parameters of spec 10 in their order: v, p..., label..., from, to, s.

    Coordinates preserve their original precision. Labels appear only when some place has
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
    return str(round_link_coordinate(x)).removesuffix(".0")


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
        f"Calendar-day-weighted {SEASON_DESCRIPTIONS[requested.season]} of each year "
        f"from {requested.from_} "
        f"to {requested.to} into one value per year. A year with a missing month has no value."
    )
    if requested.season == "DJF":
        step += " December counts toward the following year."
    return step


def _test_step(result: PlaceResult) -> str:
    name = result.place.name
    complete_years = len(result.analysis_years)
    trend = result.trend
    if complete_years == 0:
        if any(point.value is not None for point in result.series):
            return f"{name}: no common complete years were selected; no rate or test was assessed."
        return f"{name}: no year in the period has a value for every month, so no test was run."
    if trend is None:
        years = "1 complete year" if complete_years == 1 else f"{complete_years} complete years"
        return (
            f"{name}: {years}, fewer than the {MIN_YEARS_FOR_TEST} a trend test needs, "
            "so no test was run."
        )
    step = (
        f"{name}: {trend.n} complete years from {trend.first_year} to {trend.last_year}. "
        "Estimated Sen's slope using actual years; OLS slope is descriptive. "
        + (
            f"Assessed Mann-Kendall significance using {trend.method_id}. {trend.assumptions}"
            if trend.mk_p is not None
            else f"Significance was not assessed: {trend.inference_reason}"
        )
    )
    if trend.scan is not None:
        step += (
            f" Computed descriptive rates from each of {len(trend.scan)} start years "
            "that leave at least "
            f"{MIN_YEARS_FOR_TEST} years."
        )
    return step


async def map_trends(inp: MapTrendsInput, ctx: ToolContext) -> TrendMap:
    """The trend of one variable at every grid cell in a box, and of their area mean.

    The validated box preserves its coordinate precision. Cells and the fixed-footprint
    area mean have descriptive rates only: p-values are null and no cell is marked
    significant. A missing cell-month makes the area mean missing for that month.
    This conditional extension is a latest-data view, not a pinned regional analysis.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    box = _link_box(inp.box)
    _check_box(box)
    found = await ctx.source.regional_series(entry.code, box, ctx.last_complete_year)
    grid_points = sorted(found)
    point_series = [found[grid_point] for grid_point in grid_points]
    trends = [
        analyse_values(
            *_years_with_values(
                yearly_values(series.monthly, requested.season, requested.from_, requested.to)
            ),
            entry,
            requested.season,
            allow_inference=False,
        )
        for series in point_series
    ]
    area_monthly = cos_lat_weighted_mean(
        [(lat, series.monthly) for (lat, _), series in zip(grid_points, point_series, strict=True)]
    )
    area_mean = _place_result(
        entry, _area_place(box), area_monthly, requested, scan=False, allow_inference=False
    )
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


def _map_cells(
    grid_points: Sequence[tuple[float, float]], trends: Sequence[Trend | None]
) -> list[MapCell]:
    # Spec 7, "Region view": the correction runs on the final p-values of the cells that have a
    # result, so a cell without one neither counts toward it nor passes it.
    tested = {
        grid_point: trend
        for grid_point, trend in zip(grid_points, trends, strict=True)
        if trend is not None and trend.mk_p is not None
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
            f"Estimated descriptive rates for {_count(len(cells), 'grid point')}. "
            "Significance is not assessed for regional maps or their area mean."
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
