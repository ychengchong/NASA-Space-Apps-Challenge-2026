"""get_series, plus the period and fetch steps every case tool shares (spec 5; spec 7, step 1)."""

from app.catalogue import CatalogueEntry, get_entry, load_catalogue, to_summary
from app.errors import BadPeriodError, BadRequestError
from app.models import GetSeriesInput, PeriodInput, Place, Requested, Series, SeriesValue
from app.sources.base import MonthlyValues, PointSeries
from app.stats import SEASON_MONTHS, yearly_values
from app.tools.context import ToolContext
from app.tools.inference import ANALYSIS_VERSION
from app.tools.places import resolve_place


def resolve_period(
    entry: CatalogueEntry, period: PeriodInput, last_complete_year: int
) -> Requested:
    """Validate the explicit years and season without silently adjusting supported dates.

    A missing `from` is the start of the variable's record and a missing `to` is
    `last_complete_year`. Unsupported periods raise `BadPeriodError`; callers must
    confirm another period.
    """
    requested_from = period.from_ if period.from_ is not None else entry.record_start
    requested_to = period.to if period.to is not None else last_complete_year
    first_year = requested_from
    last_year = requested_to
    if first_year < entry.record_start or last_year > last_complete_year:
        raise BadPeriodError(
            f"Requested {first_year}-{last_year}; "
            f"available {entry.record_start}-{last_complete_year}. "
            "Choose and confirm a supported period; dates were not changed."
        )
    if period.analysis_version not in (None, ANALYSIS_VERSION):
        raise BadRequestError(
            "This analysis version is unavailable; no current method was substituted."
        )
    if period.snapshot_ids and period.analysis_version is None:
        raise BadRequestError("Pinned evidence requires an analysis version.")
    if first_year > last_year:
        raise BadPeriodError(
            f"This variable's record runs from {entry.record_start} to {last_complete_year}, "
            f"so the period {requested_from} to {requested_to} holds no year to analyse."
        )
    # "from" is a Python keyword, so the model is built from a dict rather than by keyword.
    return Requested.model_validate({"from": first_year, "to": last_year, "season": period.season})


async def fetch_point_series(
    entry: CatalogueEntry, place: Place, ctx: ToolContext, snapshot_id: str | None = None
) -> PointSeries:
    """The variable's full monthly record at the centre of the place's cell, up to the last
    complete year.

    Spec 6: the source is asked for every catalogue code on the variable's own grid, in
    catalogue order, so one call fetches them all and a later variable on that grid at the same
    place is read from the cache. Codes on the other grid are never asked for at this centre:
    their cell around the place has another centre, and POWER would answer them from whichever
    of their cells holds this one. The whole record is always requested, so any period can be
    cut from one cached response. Only the entry's own series is returned. Raises
    `SourceUnavailableError` when the data is neither cached nor available.
    """
    if snapshot_id is not None:
        series = ctx.snapshots.series(snapshot_id)
        if (series.code, series.lat, series.lon) != (entry.code, place.cell.lat, place.cell.lon):
            raise BadRequestError("The snapshot does not match this variable and grid cell.")
        return series
    codes = [other.code for other in load_catalogue() if other.grid == entry.grid]
    found = await ctx.source.point_series(
        place.cell.lat, place.cell.lon, codes, ctx.last_complete_year
    )
    return found[entry.code]


async def get_series(inp: GetSeriesInput, ctx: ToolContext) -> Series:
    """The raw values behind a case: monthly values or yearly means, in the variable's units.

    "monthly" lists the months of the season in each year of the period, as "YYYY-MM"; for
    "annual" that is every month, and the DJF of year Y starts with December of Y - 1. "yearly"
    lists one "YYYY" value per year, the mean used by the trend test (spec 7, step 2). A missing
    month, or a year with any missing month, has the value None. Raises `UnknownVariableError`,
    `BadPeriodError` or `SourceUnavailableError`.
    """
    entry = get_entry(inp.variable)
    requested = resolve_period(entry, inp, ctx.last_complete_year)
    place = resolve_place(inp.place, entry)
    if len(inp.snapshot_ids) > 1:
        raise BadRequestError("A series takes one snapshot.")
    point_series = await fetch_point_series(
        entry, place, ctx, inp.snapshot_ids[0] if inp.snapshot_ids else None
    )
    if inp.resolution == "monthly":
        values = _monthly_values(point_series.monthly, requested)
    else:
        values = _yearly_values(point_series.monthly, requested)
    return Series(variable=to_summary(entry), place=place, resolution=inp.resolution, values=values)


def _monthly_values(monthly: MonthlyValues, requested: Requested) -> list[SeriesValue]:
    values: list[SeriesValue] = []
    for year in range(requested.from_, requested.to + 1):
        for year_offset, month in SEASON_MONTHS[requested.season]:
            month_year = year + year_offset
            values.append(
                SeriesValue(
                    date=f"{month_year:04d}-{month:02d}", value=monthly.get((month_year, month))
                )
            )
    return values


def _yearly_values(monthly: MonthlyValues, requested: Requested) -> list[SeriesValue]:
    yearly = yearly_values(monthly, requested.season, requested.from_, requested.to)
    return [SeriesValue(date=f"{year:04d}", value=value) for year, value in yearly]
