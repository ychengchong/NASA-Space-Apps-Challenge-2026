"""analyze_trend and compare_places, one case as one Investigation, and map_trends, the trends of
every grid cell in a box as one TrendMap (spec 5; spec 7, "Method" and "Region view").
"""

import asyncio
import hashlib
import json
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import TypedDict, cast
from urllib.parse import quote, urlencode

from app.catalogue import CatalogueEntry, GridAlignment, get_entry, load_catalogue, to_summary
from app.config import DATA_DIR
from app.errors import (
    BadPlaceError,
    BadRequestError,
    SourceUnavailableError,
    UnsupportedRequestError,
)
from app.models import (
    AnalyzeTrendInput,
    Box,
    Cell,
    ComparePlacesInput,
    Contrast,
    Gap,
    Investigation,
    MapCell,
    MapTrendsInput,
    OverviewRow,
    Place,
    PlaceInput,
    PlaceOverview,
    PlaceOverviewInput,
    PlaceResult,
    PlaceSeasons,
    Records,
    RecordYear,
    Requested,
    ScanPoint,
    Season,
    SeasonRate,
    SeasonRates,
    SeasonRatesInput,
    SourceRef,
    Trend,
    TrendMap,
    Verdict,
    WorldTrend,
    WorldTrendInput,
    YearsMean,
    YearValue,
)
from app.sources.base import MonthlyValues, PointSeries
from app.stats import (
    FALSE_DISCOVERY_RATE,
    MIN_YEARS_FOR_TEST,
    all_equal,
    benjamini_hochberg,
    compute_trend,
    cos_lat_weighted_mean,
    first_and_last_means,
    rank_years,
    to_trend,
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
from app.verdict import (
    OVERVIEW_NOTE,
    RECORDS_NOTE,
    SEASONS_NOTE,
    build_verdict,
    caution_text,
    compare_places_summary,
    gap_sentence,
    overview_before_record_sentence,
    overview_sentence,
    records_sentences,
    season_rate_sentence,
    world_sample_note,
    world_verdict,
)

# Spec 5: the id is a short hash of the normalised inputs; this many hex digits of SHA-256.
CASE_ID_HEX_DIGITS = 12
# Spec 10: the web app's page for a case.
CASE_PATH = "/case"
# Spec 10: the web app's page for a trend map.
MAP_PATH = "/map"
# Spec 10: the web app's page for what is changing at one place.
OVERVIEW_PATH = "/place"
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
    gap = _gap(entry, results) if len(results) == GAP_PLACES else None
    return _investigation(
        entry,
        inp.places,
        requested,
        results,
        sources,
        ctx,
        contrast=contrast,
        summary=summary,
        gap=gap,
    )


def _gap(entry: CatalogueEntry, results: Sequence[PlaceResult]) -> Gap:
    """The first place's yearly values minus the second's over their common years, and the
    descriptive Sen rate of that gap (spec 7, "The gap between two places").

    The common years are the analysis years both results share. Fewer than ten give no rate.
    Same-cell snapshots with differing common-year values are rejected: their versions
    must not be presented as a spatial contrast. Consistent same-cell values have zero gap.
    """
    first, second = results
    years = [year for year in first.analysis_years if year in set(second.analysis_years)]
    first_values = {point.year: point.value for point in first.series}
    second_values = {point.year: point.value for point in second.series}
    differences = [_difference(first_values[year], second_values[year]) for year in years]
    trend = (
        to_trend(compute_trend(years, differences)) if len(years) >= MIN_YEARS_FOR_TEST else None
    )
    same_cell = first.place.cell == second.place.cell
    if same_cell and any(value != 0.0 for value in differences):
        raise BadRequestError(
            "These locations share a grid cell but their snapshots contain different retained "
            "values. Choose consistent evidence before making a spatial comparison."
        )
    return Gap(
        first_place=first.place.name,
        second_place=second.place.name,
        series=[
            YearValue(year=year, value=value)
            for year, value in zip(years, differences, strict=True)
        ],
        n=len(years),
        first_year=years[0] if years else None,
        last_year=years[-1] if years else None,
        sen_slope=trend.sen_slope if trend is not None else None,
        total_change=trend.total_change if trend is not None else None,
        line=trend.line if trend is not None else None,
        same_cell=same_cell,
        sentence=gap_sentence(
            entry, first.place.name, second.place.name, len(years), trend, same_cell
        ),
    )


def _difference(first: float | None, second: float | None) -> float:
    # Common years have a value at both places, so neither is None here.
    if first is None or second is None:
        raise ValueError("A common year needs a value at both places.")
    return first - second


# Spec 7, "The whole world": the frozen sample, its page, and the place its case stands for.
WORLD_MEAN_PATH = DATA_DIR / "world-mean.json"
WORLD_MEAN_SCHEMA = "world_mean_v1"
WORLD_PATH = "/world"
WORLD_NAME = "the whole world"
WORLD_HEIGHT_DEGREES = 180.0
WORLD_WIDTH_DEGREES = 360.0


class WorldSample(TypedDict):
    step_degrees: int
    latitudes: list[int]
    longitudes: list[int]
    points: int


class WorldMeanDocument(TypedDict):
    schema: str
    built: str
    end_year: int
    sample: WorldSample
    api_versions: list[str]
    accessed: list[str]
    variables: dict[str, dict[str, float | None]]


# Spec 7, "The gap between two places": a comparison of exactly this many places has a gap.
GAP_PLACES = 2
# Spec 7, "All seasons at once": the rows of the seasons panel, in this order.
SEASON_ORDER: tuple[Season, ...] = ("annual", "DJF", "MAM", "JJA", "SON")


async def season_rates(inp: SeasonRatesInput, ctx: ToolContext) -> SeasonRates:
    """The descriptive rate of each season, and of all months, at every place of a case.

    Each season is analysed exactly as the case would be with that season, from the same
    evidence: the same snapshots when the case is pinned, and in a comparison the common
    complete years of that season. Rates are per decade in the variable's rate units. No
    interval or p-value is returned. Only the all-months row of annual T2M can carry an
    assessed verdict, as the inference gate allows; every other row is descriptive. A season
    with fewer than ten complete years has no rate, and one with none has neither rate nor
    years. Raises the same errors as `analyze_trend`.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    rows: list[list[SeasonRate]] = [[] for _ in inp.places]
    places: list[Place] = []
    # One season after another: every season reads the same cached or pinned series.
    for season in SEASON_ORDER:
        period = Requested.model_validate(
            {"from": requested.from_, "to": requested.to, "season": season}
        )
        results, _ = await _analyse_places(entry, inp.places, period, False, ctx, inp.snapshot_ids)
        places = [result.place for result in results]
        for place_rows, result in zip(rows, results, strict=True):
            place_rows.append(_season_rate(entry, season, result))
    return SeasonRates(
        variable=to_summary(entry),
        requested=requested,
        places=[
            PlaceSeasons(place=place, rates=place_rows)
            for place, place_rows in zip(places, rows, strict=True)
        ],
        note=SEASONS_NOTE,
    )


def _season_rate(entry: CatalogueEntry, season: Season, result: PlaceResult) -> SeasonRate:
    trend = result.trend
    n_years = len(result.analysis_years)
    return SeasonRate(
        season=season,
        n=n_years,
        first_year=result.analysis_years[0] if result.analysis_years else None,
        last_year=result.analysis_years[-1] if result.analysis_years else None,
        sen_slope=trend.sen_slope if trend is not None else None,
        total_change=trend.total_change if trend is not None else None,
        verdict_kind=result.verdict.kind,
        assessed=trend is not None and trend.inference_status == "assessed",
        sentence=season_rate_sentence(
            entry,
            season,
            n_years,
            trend,
            result.verdict.kind,
            has_values=any(point.value is not None for point in result.series),
        ),
    )


async def place_overview(inp: PlaceOverviewInput, ctx: ToolContext) -> PlaceOverview:
    """Every catalogue variable's descriptive rate at one place (spec 7, "What is changing
    here?").

    Each variable runs over its own record within the requested period: from the later of
    `from` and its record start, to `to`. A missing `from` is the earliest record start and a
    missing `to` the last complete year. Rows keep the catalogue's order and are never ranked,
    since rates in different units cannot be compared. Rates are per decade in each variable's
    rate units; only annual T2M can carry an assessed verdict. One fetch per grid serves every
    variable on it, so a new place costs one call per grid and a cached place none. A variable
    whose record starts after `to` gets a row without years. This is a latest-data view: it
    pins no snapshots, and each row opens as an ordinary case that does. Raises
    `BadPeriodError` for an unsupported period and `SourceUnavailableError` when data is
    neither cached nor available.
    """
    catalogue = load_catalogue()
    earliest = min(catalogue, key=lambda entry: entry.record_start)
    requested = resolve_period(
        earliest,
        inp.model_copy(
            update={"from_": inp.from_ if inp.from_ is not None else earliest.record_start}
        ),
        ctx.last_complete_year,
    )
    rows: list[OverviewRow] = []
    sources: list[SourceRef] = []
    for entry in catalogue:
        place = resolve_place(inp.place, entry)
        if entry.record_start > requested.to:
            rows.append(_before_record_row(entry, place))
            continue
        period = Requested.model_validate(
            {
                "from": max(requested.from_, entry.record_start),
                "to": requested.to,
                "season": requested.season,
            }
        )
        series = await fetch_point_series(entry, place, ctx)
        result = _place_result(entry, place, series.monthly, period, scan=False)
        rows.append(_overview_row(entry, result))
        sources += [source for source in _sources(entry, [series]) if source not in sources]
    return PlaceOverview(
        name=_label(inp.place) or format_coordinates(inp.place.lat, inp.place.lon),
        lat=inp.place.lat,
        lon=inp.place.lon,
        requested=requested,
        rows=rows,
        note=OVERVIEW_NOTE,
        sources=sources,
        app_url=_overview_url(ctx, inp.place, requested),
    )


def _overview_row(entry: CatalogueEntry, result: PlaceResult) -> OverviewRow:
    trend = result.trend
    records = result.records
    highest_year = records.highest[0].year if records and records.highest else None
    lowest_year = records.lowest[0].year if records and records.lowest else None
    return OverviewRow(
        variable=to_summary(entry),
        cell=result.place.cell,
        n=len(result.analysis_years),
        first_year=result.analysis_years[0] if result.analysis_years else None,
        last_year=result.analysis_years[-1] if result.analysis_years else None,
        sen_slope=trend.sen_slope if trend is not None else None,
        total_change=trend.total_change if trend is not None else None,
        verdict_kind=result.verdict.kind,
        assessed=trend is not None and trend.inference_status == "assessed",
        highest_year=highest_year,
        lowest_year=lowest_year,
        sentence=overview_sentence(
            entry,
            len(result.analysis_years),
            trend,
            result.verdict.kind,
            highest_year,
            lowest_year,
        ),
        caution_sentences=[
            caution_text(caution, entry, trend) for caution in result.verdict.cautions
        ],
    )


def _before_record_row(entry: CatalogueEntry, place: Place) -> OverviewRow:
    return OverviewRow(
        variable=to_summary(entry),
        cell=place.cell,
        n=0,
        first_year=None,
        last_year=None,
        sen_slope=None,
        total_change=None,
        verdict_kind="no_data",
        assessed=False,
        highest_year=None,
        lowest_year=None,
        sentence=overview_before_record_sentence(entry),
    )


def _overview_url(ctx: ToolContext, place_input: PlaceInput, requested: Requested) -> str:
    return f"{ctx.public_base_url or ''}{OVERVIEW_PATH}?{_overview_query(place_input, requested)}"


def _overview_query(place_input: PlaceInput, requested: Requested) -> str:
    """The overview parameters in their order: p, label when given, from, to, s."""
    params = [("p", _link_point(place_input))]
    if _label(place_input):
        params.append(("label", _label(place_input)))
    params += [("from", str(requested.from_)), ("to", str(requested.to)), ("s", requested.season)]
    return urlencode(params, safe=",", quote_via=quote)


def load_world_mean(path: Path = WORLD_MEAN_PATH) -> WorldMeanDocument | None:
    """The frozen world-mean file (spec 7, "The whole world"), or None when it is missing or
    not of the expected schema. Read once per path.
    """
    return _read_world_mean(path)


@lru_cache(maxsize=2)
def _read_world_mean(path: Path) -> WorldMeanDocument | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict) or document.get("schema") != WORLD_MEAN_SCHEMA:
        return None
    return cast(WorldMeanDocument, document)


async def world_trend(inp: WorldTrendInput, ctx: ToolContext) -> WorldTrend:
    """The trend of one variable in the frozen world-mean sample (spec 7, "The whole world").

    The series is read from data/world-mean.json, never from NASA: the cosine-weighted monthly
    mean of a fixed sample of grid points. It is analysed like an area mean: rates per decade,
    record years, no p-value and no assessed verdict. Missing months stay missing. Raises
    `UnsupportedRequestError` for a variable the sample does not cover, `BadPeriodError` for an
    unsupported period and `SourceUnavailableError` when the file cannot be read.
    """
    entry = get_entry(inp.variable)
    if not entry.world_mean:
        raise UnsupportedRequestError(
            f"The whole-world mean covers no {entry.name.lower()}: it exists only on land or "
            "only at sea, so a world average of it would mean little."
        )
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    document = load_world_mean()
    if document is None or entry.id not in document["variables"]:
        raise SourceUnavailableError("The whole-world mean is not available on this server.")
    monthly: MonthlyValues = {
        (int(key[:4]), int(key[5:])): value
        for key, value in document["variables"][entry.id].items()
    }
    points = document["sample"]["points"]
    place = Place(
        name=WORLD_NAME,
        lat=0.0,
        lon=0.0,
        cell=Cell(lat=0.0, lon=0.0, height=WORLD_HEIGHT_DEGREES, width=WORLD_WIDTH_DEGREES),
    )
    result = _place_result(entry, place, monthly, requested, scan=False, allow_inference=False)
    result = result.model_copy(
        update={"verdict": world_verdict(entry, result.verdict, result.trend, points)}
    )
    return WorldTrend(
        variable=to_summary(entry),
        requested=requested,
        result=result,
        points=points,
        sample_note=world_sample_note(points, document["sample"]["step_degrees"]),
        steps=_world_steps(entry, requested, result, document),
        sources=[
            SourceRef(
                name=entry.source,
                version=", ".join(document["api_versions"]),
                accessed=", ".join(document["accessed"]),
                product=(
                    f"World mean of a {points}-point sample, prepared by "
                    f"scripts/build_world_mean.py on {document['built']}"
                ),
                provenance_status="prepared_sample_mean",
            )
        ],
        app_url=f"{ctx.public_base_url or ''}{WORLD_PATH}?{_world_query(entry.id, requested)}",
    )


def _world_steps(
    entry: CatalogueEntry, requested: Requested, result: PlaceResult, document: WorldMeanDocument
) -> list[str]:
    sample = document["sample"]
    return [
        _variable_step(entry),
        (
            f"Used a fixed sample of {sample['points']} grid points, one every "
            f"{sample['step_degrees']}° of latitude from {_edge(sample['latitudes'][0], 'N', 'S')} "
            f"to {_edge(sample['latitudes'][-1], 'N', 'S')} and of longitude from "
            f"{_edge(sample['longitudes'][0], 'E', 'W')}, read from data/world-mean.json, which "
            f"was prepared on {document['built']}. No NASA service is called for it."
        ),
        _period_step(requested),
        (
            "Averaged the sample points into one value per month, weighting each by the cosine "
            "of its latitude; a month missing at any point is missing."
        ),
        _capitalised(_test_step(result)),
    ]


def _world_query(variable_id: str, requested: Requested) -> str:
    """The world parameters in their order: v, from, to, s."""
    params = [
        ("v", variable_id),
        ("from", str(requested.from_)),
        ("to", str(requested.to)),
        ("s", requested.season),
    ]
    return urlencode(params, safe=",", quote_via=quote)


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
        records=_records(entry, years, values) if trend is not None else None,
    )


def _records(entry: CatalogueEntry, years: list[int], values: list[float]) -> Records:
    """The record years of the years the analysis used (spec 7, "Record years").

    Descriptive only: the highest and lowest yearly values, and the mean of the last ten years
    used against the first ten when there are at least twenty. When every year has the same
    value nothing is ranked.
    """
    windows = first_and_last_means(years, values)
    first_ten = (
        YearsMean(years=list(windows.first_years), mean=windows.first_mean) if windows else None
    )
    last_ten = (
        YearsMean(years=list(windows.last_years), mean=windows.last_mean) if windows else None
    )
    change = windows.change if windows else None
    if all_equal(values):
        return Records(
            highest=[],
            lowest=[],
            highest_tied=0,
            lowest_tied=0,
            first_ten=first_ten,
            last_ten=last_ten,
            change=change,
            sentences=records_sentences(
                entry, [], [], 0, 0, first_ten, last_ten, change, same_value=values[0]
            ),
            note=RECORDS_NOTE,
        )
    top = rank_years(years, values, highest=True)
    bottom = rank_years(years, values, highest=False, exclude=top.years)
    highest = [RecordYear(year=y, value=v) for y, v in zip(top.years, top.values, strict=True)]
    lowest = [RecordYear(year=y, value=v) for y, v in zip(bottom.years, bottom.values, strict=True)]
    return Records(
        highest=highest,
        lowest=lowest,
        highest_tied=top.tied,
        lowest_tied=bottom.tied,
        first_ten=first_ten,
        last_ten=last_ten,
        change=change,
        sentences=records_sentences(
            entry, highest, lowest, top.tied, bottom.tied, first_ten, last_ten, change
        ),
        note=RECORDS_NOTE,
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
    gap: Gap | None = None,
) -> Investigation:
    query = _case_query(entry.id, place_inputs, requested)
    identities = [result.snapshot_id for result in results]
    params = [("snap", identity) for identity in identities if identity is not None]
    query += "&" + urlencode([*params, ("av", ANALYSIS_VERSION)])
    # Spec 5: the scan and the record years are descriptive displays derived from the evidence
    # and the analysis years already bound here, so they leave the investigation ID unchanged.
    normalized = [result.model_dump(mode="json", exclude={"records"}) for result in results]
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
        gap=gap,
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
