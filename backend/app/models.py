"""Pydantic models for every type in spec section 5.

Each type is defined once here and reused by the REST, chat and MCP adapters.
Missing data is `None` in Python and `null` in JSON.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Season = Literal["annual", "DJF", "MAM", "JJA", "SON"]
Resolution = Literal["monthly", "yearly"]
VerdictKind = Literal["significant", "not_significant", "too_few_years", "no_data"]
Direction = Literal["rising", "falling"]
Contrast = Literal["opposite_directions", "same_direction", "unclear"]
Caution = Literal[
    "source_change",
    "variable_note",
    "short_record",
    "autocorrelated",
    "methods_disagree",
    "borderline",
]

# Spec 5 and 10: a place label is display text of 40 characters at most.
PLACE_NAME_MAX_LENGTH = 40
# Spec 5: compare_places takes two to four places.
MIN_COMPARE_PLACES = 2
MAX_COMPARE_PLACES = 4


class Model(BaseModel):
    """Base for every model: fields named `from_` travel as `from` in JSON and tool schemas."""

    model_config = ConfigDict(
        extra="forbid",
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


# Inputs (spec 5, "Inputs")


class PlaceInput(Model):
    lat: float = Field(ge=-90, le=90, description="Latitude in degrees north, -90 to 90.")
    lon: float = Field(ge=-180, le=180, description="Longitude in degrees east, -180 to 180.")
    name: str | None = Field(
        default=None,
        max_length=PLACE_NAME_MAX_LENGTH,
        description="Optional display name, shown as plain text.",
    )


class PeriodInput(Model):
    from_: int | None = Field(
        default=None,
        alias="from",
        description="First year, inclusive. Defaults to the start of the variable's record.",
    )
    to: int | None = Field(
        default=None,
        description="Last year, inclusive. Defaults to the last complete year.",
    )
    season: Season = Field(
        default="annual",
        description=(
            "annual, or a season named by its months: DJF = December to February, "
            "MAM = March to May, JJA = June to August, SON = September to November."
        ),
    )


class Box(Model):
    south: float = Field(ge=-90, le=90)
    west: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)


class SearchVariablesInput(Model):
    query: str | None = Field(default=None, description="Words to match, such as 'rain'.")
    theme: str | None = Field(default=None, description="Optional theme, such as 'temperature'.")


class FindPlaceInput(Model):
    query: str = Field(min_length=1, description="A place name, such as 'Nairobi'.")


class AnalyzeTrendInput(PeriodInput):
    variable: str = Field(description="A catalogue variable id, such as 'air_temp'.")
    place: PlaceInput
    scan: bool = Field(default=False, description="Include the period scan (spec 7, step 10).")


class ComparePlacesInput(PeriodInput):
    variable: str = Field(description="A catalogue variable id, such as 'air_temp'.")
    places: list[PlaceInput] = Field(min_length=MIN_COMPARE_PLACES, max_length=MAX_COMPARE_PLACES)
    scan: bool = Field(default=False, description="Include the period scan (spec 7, step 10).")


class GetSeriesInput(PeriodInput):
    variable: str = Field(description="A catalogue variable id, such as 'air_temp'.")
    place: PlaceInput
    resolution: Resolution


class MapTrendsInput(PeriodInput):
    variable: str = Field(description="A catalogue variable id, such as 'air_temp'.")
    box: Box


# Results (spec 5, "Result types")


class VariableSummary(Model):
    id: str
    name: str
    definition: str
    units: str
    rate_units: str
    decimals: int
    theme: str
    record_start: int
    related: list[str]
    region_types: list[str] = Field(default_factory=list)
    trend_note: str | None = None
    source_changes: list[int] | None = None


class PlaceCandidate(Model):
    name: str
    country: str | None = None
    lat: float
    lon: float
    kind: Literal["city", "region"]
    region_type: str | None = None


class Cell(Model):
    lat: float
    lon: float
    height: float
    width: float


class Place(Model):
    name: str
    lat: float
    lon: float
    cell: Cell


class SeriesValue(Model):
    date: str
    value: float | None


class Series(Model):
    variable: VariableSummary
    place: Place
    resolution: Resolution
    values: list[SeriesValue]


class Requested(Model):
    from_: int = Field(alias="from")
    to: int
    season: Season


class YearValue(Model):
    year: int
    value: float | None


class ScanPoint(Model):
    start: int
    sen_slope: float
    mk_p: float


class Trend(Model):
    n: int
    first_year: int
    last_year: int
    sen_slope: float
    sen_ci95: tuple[float, float]
    line: tuple[float, float]
    total_change: float
    mk_p: float
    lag1: float
    variance_factor: float
    ols_slope: float
    ols_p: float
    scan: list[ScanPoint] | None = None


class Verdict(Model):
    kind: VerdictKind
    direction: Direction | None
    sentence: str
    cautions: list[Caution]


class PlaceResult(Model):
    place: Place
    series: list[YearValue]
    trend: Trend | None
    verdict: Verdict


class SourceRef(Model):
    name: str
    version: str
    accessed: str


class Investigation(Model):
    id: str
    variable: VariableSummary
    requested: Requested
    results: list[PlaceResult]
    contrast: Contrast | None = None
    summary: str | None = None
    steps: list[str]
    sources: list[SourceRef]
    app_url: str


class MapCell(Model):
    lat: float
    lon: float
    sen_slope: float | None
    mk_p: float | None
    significant: bool


class TrendMap(Model):
    variable: VariableSummary
    requested: Requested
    box: Box
    cells: list[MapCell]
    area_mean: PlaceResult
    steps: list[str]
    sources: list[SourceRef]
    app_url: str
