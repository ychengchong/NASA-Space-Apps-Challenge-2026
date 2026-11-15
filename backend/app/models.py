"""Pydantic models for every type in spec section 5.

Each type is defined once here and reused by the REST, chat and MCP adapters.
Missing data is `None` in Python and `null` in JSON.
"""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Season = Literal["annual", "DJF", "MAM", "JJA", "SON"]
Resolution = Literal["monthly", "yearly"]
VerdictKind = Literal[
    "significant", "not_significant", "too_few_years", "no_data", "inference_unavailable"
]
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
    snapshot_ids: list[str] = Field(default_factory=list, max_length=4)
    analysis_version: str | None = None
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


class SeasonRatesInput(PeriodInput):
    variable: str = Field(description="A catalogue variable id, such as 'air_temp'.")
    places: list[PlaceInput] = Field(min_length=1, max_length=MAX_COMPARE_PLACES)


class PlaceOverviewInput(PeriodInput):
    place: PlaceInput


class WorldTrendInput(PeriodInput):
    variable: str = Field(description="A catalogue variable id, such as 'air_temp'.")


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
    world_mean: bool = False


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
    mk_p: float | None


class Trend(Model):
    n: int
    first_year: int
    last_year: int
    sen_slope: float
    sen_ci95: tuple[float, float] | None
    line: tuple[float, float]
    total_change: float
    mk_p: float | None
    lag1: float | None
    variance_factor: float
    ols_slope: float
    ols_p: float | None
    inference_status: Literal["assessed", "unavailable"] = "unavailable"
    inference_reason: str | None = None
    method_id: str | None = None
    ci_method: str | None = None
    aggregation: str = "calendar_day_weighted_mean_v1"
    assumptions: str | None = None
    scan: list[ScanPoint] | None = None


class Verdict(Model):
    kind: VerdictKind
    direction: Direction | None
    sentence: str
    cautions: list[Caution]


class RecordYear(Model):
    year: int
    value: float


class YearsMean(Model):
    years: list[int]
    mean: float


class Records(Model):
    """Spec 7, "Record years": descriptive facts about the years the analysis used; not tests."""

    highest: list[RecordYear]
    lowest: list[RecordYear]
    highest_tied: int
    lowest_tied: int
    first_ten: YearsMean | None
    last_ten: YearsMean | None
    change: float | None
    sentences: list[str]
    note: str


class PlaceResult(Model):
    place: Place
    series: list[YearValue]
    trend: Trend | None
    verdict: Verdict
    analysis_years: list[int] = Field(default_factory=list)
    snapshot_id: str | None = None
    records: Records | None = None


class SeasonRate(Model):
    """Spec 7, "All seasons at once": one season's descriptive rate at one place."""

    season: Season
    n: int
    first_year: int | None
    last_year: int | None
    sen_slope: float | None
    total_change: float | None
    verdict_kind: VerdictKind
    assessed: bool
    sentence: str


class PlaceSeasons(Model):
    place: Place
    rates: list[SeasonRate]


class SeasonRates(Model):
    variable: VariableSummary
    requested: Requested
    places: list[PlaceSeasons]
    note: str


class OverviewRow(Model):
    """Spec 7, "What is changing here?": one variable's descriptive rate at the place."""

    variable: VariableSummary
    cell: Cell
    n: int
    first_year: int | None
    last_year: int | None
    sen_slope: float | None
    total_change: float | None
    verdict_kind: VerdictKind
    assessed: bool
    highest_year: int | None
    lowest_year: int | None
    sentence: str
    caution_sentences: list[str] = Field(default_factory=list)


class SourceRef(Model):
    name: str
    version: str
    accessed: str
    url: str = "https://power.larc.nasa.gov/"
    product: str = "Product release not recorded in legacy cache"
    snapshot_id: str | None = None
    raw_sha256: str | None = None
    provenance_status: str = "legacy_normalized_cache"


class Gap(Model):
    """Spec 7, "The gap between two places": the first place's yearly value minus the second's,
    over the comparison's common years. Descriptive; the difference is never tested.
    """

    first_place: str
    second_place: str
    series: list[YearValue]
    n: int
    first_year: int | None
    last_year: int | None
    sen_slope: float | None
    total_change: float | None
    line: tuple[float, float] | None
    same_cell: bool
    sentence: str


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
    analysis_version: str = "td-2026-11-v1"
    common_years: list[int] | None = None
    pinned: bool = False
    gap: Gap | None = None


class PlaceOverview(Model):
    name: str
    lat: float
    lon: float
    requested: Requested
    rows: list[OverviewRow]
    note: str
    sources: list[SourceRef]
    app_url: str


class WorldTrend(Model):
    """Spec 7, "The whole world": a variable's trend in a frozen world-mean sample."""

    variable: VariableSummary
    requested: Requested
    result: PlaceResult
    points: int
    sample_note: str
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


# Spec 5 and 8: one question of at most 2,000 characters, for every AI path.
QUESTION_MAX_LENGTH = 2000


class PlannerRequest(Model):
    question: str = Field(min_length=1, max_length=QUESTION_MAX_LENGTH)


# Spec 8, "When the AI is off": one setting that keeps an AI path off. Each names the setting to
# change, never its value, so a key or a store ID is never reported.
AiSetupGap = Literal[
    "ai_disabled",
    "no_ai_provider",
    "ai_not_evaluated",
    "no_ai_model",
    "no_openai_api_key",
    "no_anthropic_api_key",
    "no_ollama_digest",
    "budget_not_durable",
    "no_daily_budget",
    "no_token_prices",
    "provider_not_openai",
    "rag_disabled",
    "no_vector_store",
    "malformed_vector_store",
    "no_corpus_version",
    "no_corpus_manifest",
    "corpus_version_mismatch",
    "no_search_price",
    "discovery_not_evaluated",
    "explanations_not_evaluated",
]


class Capabilities(Model):
    """Spec 8: each AI path reports its availability separately; a working planner does not
    imply working retrieval. A path's gaps list what keeps it off, and are empty when it is
    available. The newer fields have defaults so older clients still parse.
    """

    ai_planner_available: bool
    ai_discovery_available: bool = False
    ai_explanation_available: bool = False
    ai_planner_gaps: list[AiSetupGap] = Field(default_factory=list)
    ai_discovery_gaps: list[AiSetupGap] = Field(default_factory=list)
    ai_explanation_gaps: list[AiSetupGap] = Field(default_factory=list)


class ExtractedPlan(Model):
    model_config = ConfigDict(strict=True)
    variable: str | None
    place_queries: list[str] = Field(max_length=2)
    from_: int | None = Field(alias="from")
    to: int | None
    season: Season
    ambiguous: bool


class Proposal(Model):
    variables: list[VariableSummary]
    places: list[PlaceCandidate]
    from_: int | None = Field(alias="from")
    to: int | None
    season: Season
    notices: list[str]
    written_by_ai: bool = True


# Discovery and explanation (spec 5, "Planned discovery and explanation contracts")

# Spec 5: an investigation ID is the SHA-256 of its evidence, written as 64 lowercase hex.
SHA256_PATTERN = r"^[0-9a-f]{64}$"
# A manifest source ID: a short slug that can never hold spaces, quotes or a URL scheme.
SOURCE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.#/-]{0,119}$"
SOURCE_ID_MAX_LENGTH = 120
# A manifest section ID: its source ID and a section number, as the corpus build writes it.
SECTION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.#/-]{0,127}$"
SECTION_ID_MAX_LENGTH = 128
# An OpenAI file ID; the bound only keeps a malformed provider value from growing a response.
FILE_ID_MAX_LENGTH = 200
# Citation links come from the reviewed manifest and are always HTTPS (spec 5).
HTTPS_URL_PATTERN = r"^https://[^\s]+$"
URL_MAX_LENGTH = 500
TITLE_MAX_LENGTH = 300
SECTION_MAX_LENGTH = 300
CORPUS_VERSION_MAX_LENGTH = 128
VARIABLE_ID_MAX_LENGTH = 64
# Spec 8, "Planned corpus and retrieval": at most four passages of at most 1,200 characters.
# A citation names one retrieved passage, so a list of citations is bounded by MAX_PASSAGES too.
PASSAGE_MAX_LENGTH = 1200
MAX_PASSAGES = 4
# Spec 8, "Planned guided discovery": up to three suggestions and four clarification choices.
MAX_SUGGESTIONS = 3
MAX_CLARIFICATION_CHOICES = 4
REASON_MAX_LENGTH = 600
CLARIFICATION_MAX_LENGTH = 300
CHOICE_LABEL_MAX_LENGTH = 80
MAX_NOTICES = 8
BLOCK_TEXT_MAX_LENGTH = 1200
MAX_BLOCKS = 6
MAX_REFERENCES = 8

SourceKind = Literal["agency", "project"]
# Spec 8: the draft fields a discovery answer can report as still missing.
DraftField = Literal["variable", "place", "from", "to", "season"]
# Spec 5: why a discovery or explanation gave no finding, so retrieval absence, a provider
# refusal or incomplete output, output that failed validation and an unsupported question are
# never confused with one another or with a valid finding.
UnansweredReason = Literal[
    "no_evidence",
    "provider_refused",
    "provider_incomplete",
    "validation_failed",
    "unsupported_question",
]
# Spec 8, "Planned explanations": the Investigation fields an answer may point at. The frontend
# renders each one from the trusted Investigation; the model never writes the value itself.
ResultField = Literal[
    "sen_slope",
    "sen_ci95",
    "mk_p",
    "total_change",
    "n",
    "first_year",
    "last_year",
    "verdict.kind",
    "verdict.sentence",
    "place.name",
    "variable.name",
    "variable.units",
    "variable.rate_units",
    "requested.from",
    "requested.to",
    "requested.season",
]


class DocumentSource(Model):
    """One reviewed corpus section with its original metadata (spec 5, spec 8 "Corpus")."""

    source_id: str = Field(pattern=SOURCE_ID_PATTERN, max_length=SOURCE_ID_MAX_LENGTH)
    section_id: str = Field(pattern=SECTION_ID_PATTERN, max_length=SECTION_ID_MAX_LENGTH)
    publisher: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    url: str = Field(pattern=HTTPS_URL_PATTERN, max_length=URL_MAX_LENGTH)
    section: str = Field(max_length=SECTION_MAX_LENGTH)
    accessed: date
    version: str | None = None
    sha256: str = Field(pattern=SHA256_PATTERN)
    # "project" marks the project's own method notes, never attributed to NASA.
    kind: SourceKind


class RetrievedPassage(Model):
    """One vector-store hit. A ranking signal and evidence to check, not proof of support."""

    source_id: str = Field(pattern=SOURCE_ID_PATTERN, max_length=SOURCE_ID_MAX_LENGTH)
    section_id: str = Field(pattern=SECTION_ID_PATTERN, max_length=SECTION_ID_MAX_LENGTH)
    text: str = Field(min_length=1, max_length=PASSAGE_MAX_LENGTH)
    file_id: str = Field(min_length=1, max_length=FILE_ID_MAX_LENGTH)
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    score: float = Field(allow_inf_nan=False)


class Citation(Model):
    """A cited passage as the server builds it, never from model text (spec 5, spec 8).

    The source fields and `section` (the section title) come from the manifest; `passage` is
    the retrieved text itself, so the interface can show the cited passage in its context.
    """

    source_id: str = Field(pattern=SOURCE_ID_PATTERN, max_length=SOURCE_ID_MAX_LENGTH)
    section_id: str = Field(pattern=SECTION_ID_PATTERN, max_length=SECTION_ID_MAX_LENGTH)
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    publisher: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    url: str = Field(pattern=HTTPS_URL_PATTERN, max_length=URL_MAX_LENGTH)
    section: str = Field(max_length=SECTION_MAX_LENGTH)
    kind: SourceKind
    passage: str = Field(min_length=1, max_length=PASSAGE_MAX_LENGTH)


class DiscoveryDraft(Model):
    """The browser's typed, unconfirmed settings, resubmitted instead of chat history."""

    variable: str | None = Field(default=None, max_length=VARIABLE_ID_MAX_LENGTH)
    places: list[PlaceInput] = Field(default_factory=list, max_length=MAX_COMPARE_PLACES)
    from_: int | None = Field(default=None, alias="from")
    to: int | None = None
    season: Season | None = None


class DiscoveryRequest(Model):
    question: str = Field(min_length=1, max_length=QUESTION_MAX_LENGTH)
    draft: DiscoveryDraft | None = None


class VariableSuggestion(Model):
    """A supported variable worth investigating, with a cited qualitative reason (spec 8)."""

    variable: VariableSummary
    reason: str = Field(min_length=1, max_length=REASON_MAX_LENGTH)
    citations: list[Citation] = Field(min_length=1, max_length=MAX_PASSAGES)


class ClarificationChoice(Model):
    """One answer to a clarification: the draft fields it would set, resolved by the server.

    The place is a reviewed `find_place` match, never model-written coordinates.
    """

    label: str = Field(min_length=1, max_length=CHOICE_LABEL_MAX_LENGTH)
    variable: str | None = Field(default=None, max_length=VARIABLE_ID_MAX_LENGTH)
    place: PlaceCandidate | None = None
    from_: int | None = Field(default=None, alias="from")
    to: int | None = None
    season: Season | None = None


class Clarification(Model):
    question: str = Field(min_length=1, max_length=CLARIFICATION_MAX_LENGTH)
    choices: list[ClarificationChoice] = Field(max_length=MAX_CLARIFICATION_CHOICES)


class DiscoveryResponse(Model):
    """Spec 5: suggestions and a proposal awaiting confirmation; nothing has been run.

    `reason` says why a discovery is "unsupported" and is null for "ready" and "clarify".
    """

    status: Literal["ready", "clarify", "unsupported"]
    reason: UnansweredReason | None = None
    suggestions: list[VariableSuggestion] = Field(max_length=MAX_SUGGESTIONS)
    proposal: Proposal | None = None
    missing: list[DraftField]
    clarification: Clarification | None = None
    notices: list[str] = Field(max_length=MAX_NOTICES)
    written_by_ai: bool = True
    corpus_version: str = Field(min_length=1, max_length=CORPUS_VERSION_MAX_LENGTH)

    @model_validator(mode="after")
    def _reason_matches_status(self) -> Self:
        _check_reason(self.status == "unsupported", self.reason)
        return self


class ExplanationRequest(Model):
    question: str = Field(min_length=1, max_length=QUESTION_MAX_LENGTH)
    investigation_id: str = Field(pattern=SHA256_PATTERN)


class ResultReference(Model):
    """An allowlisted Investigation field; `place` indexes `results` for per-place fields."""

    field: ResultField
    place: int = Field(default=0, ge=0, lt=MAX_COMPARE_PLACES)


class ExplanationBlock(Model):
    text: str = Field(min_length=1, max_length=BLOCK_TEXT_MAX_LENGTH)
    citations: list[Citation] = Field(max_length=MAX_PASSAGES)
    references: list[ResultReference] = Field(max_length=MAX_REFERENCES)


class ExplanationResponse(Model):
    """Spec 5: qualitative blocks bound to one server-loaded investigation.

    `reason` says why an answer is "insufficient_evidence" and is null for the other statuses.
    """

    status: Literal["answered", "insufficient_evidence", "new_investigation_required"]
    reason: UnansweredReason | None = None
    investigation_id: str = Field(pattern=SHA256_PATTERN)
    corpus_version: str = Field(min_length=1, max_length=CORPUS_VERSION_MAX_LENGTH)
    blocks: list[ExplanationBlock] = Field(max_length=MAX_BLOCKS)
    proposal: Proposal | None = None
    written_by_ai: bool = True

    @model_validator(mode="after")
    def _reason_matches_status(self) -> Self:
        _check_reason(self.status == "insufficient_evidence", self.reason)
        return self


def _check_reason(unanswered: bool, reason: UnansweredReason | None) -> None:
    """Spec 5: an unanswered status names its reason, and a finding never carries one."""
    if unanswered and reason is None:
        raise ValueError("An unanswered status needs a reason.")
    if not unanswered and reason is not None:
        raise ValueError("Only an unanswered status has a reason.")
