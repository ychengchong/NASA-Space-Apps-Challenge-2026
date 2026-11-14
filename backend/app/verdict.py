"""Verdict rules, cautions and the sentence templates of spec section 7.

This module owns every user-facing sentence about a result. It computes no statistics: it
reads a `Trend` whose slopes are already per decade, and fills fixed templates.
"""

from collections.abc import Sequence

from app.catalogue import CatalogueEntry
from app.models import (
    MIN_COMPARE_PLACES,
    Caution,
    Contrast,
    Direction,
    PlaceResult,
    RecordYear,
    Season,
    Trend,
    Verdict,
    VerdictKind,
    YearsMean,
)
from app.stats import MIN_YEARS_FOR_TEST, SHORT_RECORD_YEARS, SIGNIFICANCE_LEVEL

# Spec 7, "Cautions": r1 of this or more adds the "autocorrelated" caution.
AUTOCORRELATED_R1 = 0.3
# Spec 7, "Cautions": a p-value from BORDERLINE_P_LOW to BORDERLINE_P_HIGH, both included,
# adds the "borderline" caution.
BORDERLINE_P_LOW = 0.025
BORDERLINE_P_HIGH = 0.10

# Spec 7, "Verdict sentences". {amount} is the rate followed by the rate units, if any.
_SIGNIFICANT_TEMPLATE = (
    "The estimated change in {Variable} for the grid cell containing {place} is "
    "{amount} per decade from {first_year} to {last_year}. Evidence for a monotonic "
    "trend meets the stated test's 5% threshold, conditional on its assumptions."
)
_NOT_SIGNIFICANT_TEMPLATE = (
    "{Variable} in {place} changed by about {amount} per decade from {first_year} to "
    "{last_year}. These data do not provide sufficient evidence for a monotonic trend "
    "under the stated test. This does not establish that no change occurred."
)
_ZERO_SLOPE_TEMPLATE = (
    "The estimated Sen slope for {Variable} in {place} is zero from {first_year} to "
    "{last_year}. This does not establish that no change occurred."
)
_TOO_FEW_YEARS_TEMPLATE = (
    "There are only {n} complete years of {variable} data here. "
    "That is too few to test for a trend."
)
_ONE_YEAR_TEMPLATE = (
    "There is only 1 complete year of {variable} data here. That is too few to test for a trend."
)
_NO_DATA_TEMPLATE = "There is no {variable} data for this location."

# A small value that rounds to zero gets more digits, up to this many (spec 7, "Record years").
MAX_SMALL_VALUE_DECIMALS = 12
# Spec 7, "Record years": descriptive facts about the years used, never tests.
_HIGHEST_TEMPLATE = "Highest yearly values used ({units}): {values}."
_LOWEST_TEMPLATE = "Lowest yearly values used ({units}): {values}."
_ONE_TIED_TEMPLATE = "1 more year has the same value as {year}."
_MANY_TIED_TEMPLATE = "{n} more years have the same value as {year}."
_SAME_VALUE_TEMPLATE = "Every year used has the same value ({units}): {value}."
_WINDOW_TEMPLATE = (
    "The mean of the last ten years used, {last_first} to {last_last}, was {amount} "
    "{higher_or_lower} than the mean of the first ten, {first_first} to {first_last}."
)
_WINDOW_SAME_TEMPLATE = (
    "The mean of the last ten years used, {last_first} to {last_last}, was the same as the "
    "mean of the first ten, {first_first} to {first_last}."
)
# Spec 7, "All seasons at once": one sentence per season and place, and the panel's fixed note.
SEASON_NAMES: dict[Season, str] = {
    "annual": "Every month",
    "DJF": "December to February",
    "MAM": "March to May",
    "JJA": "June to August",
    "SON": "September to November",
}
_SEASON_RATE_TEMPLATE = (
    "{season}: {amount} per decade from {first_year} to {last_year}, over {n} complete years."
)
_SEASON_NOT_ASSESSED = "Significance was not assessed."
_SEASON_ASSESSED_TEMPLATE = "The trend test for all months finds it {kind}."
_SEASON_TOO_FEW_TEMPLATE = "{season}: {years}, too few for a rate."
_SEASON_NO_COMMON_YEAR_TEMPLATE = "{season}: no complete year in common with the other places."
_SEASON_NO_YEAR_TEMPLATE = "{season}: no complete year to use."
SEASONS_NOTE = (
    "Each rate is descriptive. Rates for different seasons can differ by chance alone, and no "
    "difference between seasons was tested."
)
# Spec 7, "What is changing here?": one sentence per variable and the view's fixed note.
_OVERVIEW_RATE_TEMPLATE = (
    "{amount} per decade from {first_year} to {last_year}, {total} in all, over {n} complete years"
)
_OVERVIEW_RECORDS_TEMPLATE = "; highest in {highest}, lowest in {lowest}"
_OVERVIEW_SAME_VALUE = "; every year has the same value"
_OVERVIEW_ASSESSED_TEMPLATE = "The trend test finds it {kind}."
_OVERVIEW_TOO_FEW_TEMPLATE = "{years}, too few for a rate."
_OVERVIEW_NO_YEAR = "No year in the period has a value for every month."
_OVERVIEW_BEFORE_RECORD_TEMPLATE = "Its record starts in {record_start}, after the period ends."
OVERVIEW_NOTE = (
    "This view cannot say which of these changes are real. Every rate is descriptive, except "
    "that annual air temperature reports its trend test. Rates in different units cannot be "
    "compared by size, so the variables keep the catalogue's order."
)
# Spec 7, "The gap between two places": true for every combination of signs, and never a test.
_GAP_TEMPLATE = (
    "The difference between {first} and {second}, {first} minus {second}, changed by about "
    "{amount} per decade from {first_year} to {last_year}, over {n} common years. A positive "
    "rate means {first} rose compared with {second}. The difference was not tested; this is a "
    "description."
)
_GAP_SAME_CELL_TEMPLATE = (
    "{first} and {second} are in the same grid cell, so the difference between them is zero "
    "in every year."
)
_GAP_TOO_FEW_TEMPLATE = (
    "{first} and {second} have {n} common complete years, too few for a rate of their difference."
)
_GAP_NO_YEAR_TEMPLATE = (
    "{first} and {second} have no common complete year, so there is no difference to describe."
)
# Spec 7, "The whole world": the verdict sentence of a world mean, whose place is no grid cell,
# and the note every world page carries.
_WORLD_TEMPLATE = (
    "The estimated change in {variable} averaged over a sample of {points} grid points across "
    "the whole world is {amount} per decade over {first_year}-{last_year}. This is an estimate "
    "from a sample, and significance has not been assessed."
)
_WORLD_SAMPLE_NOTE_TEMPLATE = (
    "This is an estimate from a sample of {points} grid points, one every {step}° of latitude "
    "and longitude, each weighted by the cosine of its latitude. A sample describes world "
    "temperature far better than world rainfall or wind, which change over short distances."
)
RECORDS_NOTE = (
    "These facts describe the yearly values used. They are not tests, and their significance "
    "was not assessed."
)

# Spec 7, "Cautions": what the user reads.
_SOURCE_CHANGE_TEMPLATE = (
    "The data source for this variable changes in {years}, which can create an artificial step."
)
_FIXED_CAUTION_TEXTS: dict[Caution, str] = {
    "short_record": (
        "This record is short. Trends in short records often fade as more years arrive."
    ),
    "autocorrelated": (
        "Year-to-year dependence is present. "
        "Check the stated assumptions; other dependence may invalidate inference."
    ),
    "methods_disagree": "Two standard methods disagree about this trend.",
    "borderline": "This result is close to the threshold for significance.",
}


def format_rate(rate_per_decade: float, decimals: int) -> str:
    """Return the size of a rate per decade as text, without a sign (spec 7, `{rate}`).

    The size is rounded to `decimals` digits. If that rounds to zero, one more digit is
    shown, so 0.004 with 2 decimals reads "0.004". Rounding is that of Python's format(), which
    the frontend's formatRate copies so the screen and the sentence show the same digits: a
    value exactly halfway rounds to the even digit, so 0.125 with 2 decimals reads "0.12".
    """
    size = abs(rate_per_decade)
    text = f"{size:.{decimals}f}"
    if size == 0:
        return f"{size:.{decimals + 1}f}"
    precision = decimals
    while float(text) == 0 and precision < 12:
        precision += 1
        text = f"{size:.{precision}f}"
    return text


def format_signed_rate(rate_per_decade: float, decimals: int) -> str:
    """Return the digits of `format_rate` with a leading "+" or "-" (spec 7, `{signed rate}`).

    An exactly zero rate carries no sign.
    """
    digits = format_rate(rate_per_decade, decimals)
    if rate_per_decade > 0:
        return f"+{digits}"
    if rate_per_decade < 0:
        return f"-{digits}"
    return digits


def build_verdict(
    entry: CatalogueEntry, place_name: str, n_years: int, trend: Trend | None
) -> Verdict:
    """Return the verdict for one place: kind, direction, sentence and cautions (spec 7).

    `n_years` counts the yearly values that have data. `trend` is None exactly when
    `n_years` is below MIN_YEARS_FOR_TEST; its slopes are per decade. Without a trend, the
    only caution is `variable_note`, when the variable has a trend note. Raises ValueError
    when a record long enough to test comes without a trend.
    """
    variable = _variable_mid_sentence(entry)
    if n_years == 0:
        return Verdict(
            kind="no_data",
            direction=None,
            sentence=_NO_DATA_TEMPLATE.format(variable=variable),
            cautions=_cautions(entry, None),
        )
    if n_years < MIN_YEARS_FOR_TEST:
        return Verdict(
            kind="too_few_years",
            direction=None,
            sentence=_too_few_years_sentence(n_years, variable),
            cautions=_cautions(entry, None),
        )
    if trend is None:
        raise ValueError(f"A record of {n_years} yearly values needs a trend.")
    if trend.mk_p is None or trend.inference_status != "assessed":
        reason = trend.inference_reason or "The inference method is not validated for this case."
        return Verdict(
            kind="inference_unavailable",
            direction=None,
            sentence=(
                f"The estimated change in {variable} for the grid cell containing "
                f"{place_name} is {format_signed_rate(trend.sen_slope, entry.decimals)} "
                f"{entry.rate_units} per decade over {trend.first_year}-{trend.last_year}. "
                f"{reason} "
                "Significance has not been assessed."
            ),
            cautions=_cautions(entry, trend),
        )
    kind, direction = _kind_and_direction(trend)
    return Verdict(
        kind=kind,
        direction=direction,
        sentence=_trend_sentence(entry, place_name, trend, kind),
        cautions=_cautions(entry, trend),
    )


def caution_text(caution: Caution, entry: CatalogueEntry, trend: Trend | None = None) -> str:
    """Return the text the user reads for a caution (spec 7, "Cautions").

    `source_change` names the change years that `trend` crosses, so it needs the trend.
    `variable_note` returns the entry's own `trend_note`. Raises ValueError when the
    caution cannot apply to the entry and trend given.
    """
    if caution == "source_change":
        years = _crossed_source_changes(entry, trend) if trend is not None else []
        if not years:
            raise ValueError("The source_change caution needs a trend that crosses a change.")
        return _SOURCE_CHANGE_TEMPLATE.format(years=_join([str(year) for year in years]))
    if caution == "variable_note":
        if not entry.trend_note:
            raise ValueError(f"'{entry.id}' has no trend note.")
        return entry.trend_note
    return _FIXED_CAUTION_TEXTS[caution]


def compare_places_summary(
    entry: CatalogueEntry, results: Sequence[PlaceResult]
) -> tuple[Contrast, str]:
    """Return the contrast between places and its summary sentence (spec 7, "Comparing places").

    Only significant trends count toward a direction, so a place without a significant
    trend never makes the places opposite. Raises ValueError for fewer than two places.
    """
    if len(results) < MIN_COMPARE_PLACES:
        raise ValueError(f"A comparison needs at least {MIN_COMPARE_PLACES} places.")
    years = results[0].analysis_years
    if not years or any(result.analysis_years != years for result in results):
        return "unclear", "No common complete years are available for a descriptive comparison."
    usable = [result for result in results if result.trend is not None]
    if len(usable) != len(results):
        return (
            "unclear",
            "Too few common values to estimate all rates. Significance has not been compared.",
        )
    rates = "; ".join(
        f"{result.place.name}: {format_signed_rate(result.trend.sen_slope, entry.decimals)} "
        f"{entry.rate_units} per decade"
        for result in usable
    )
    signs = {
        1 if result.trend.sen_slope > 0 else -1 if result.trend.sen_slope < 0 else 0
        for result in usable
    }
    contrast: Contrast = (
        "opposite_directions"
        if signs == {-1, 1}
        else "same_direction"
        if len(signs) == 1 and 0 not in signs
        else "unclear"
    )
    return contrast, (
        f"Descriptive comparison on {len(years)} identical complete years "
        f"({years[0]}-{years[-1]}): {rates}. "
        "This is not a statistical test of differences between places."
    )


def records_sentences(
    entry: CatalogueEntry,
    highest: Sequence[RecordYear],
    lowest: Sequence[RecordYear],
    highest_tied: int,
    lowest_tied: int,
    first_ten: YearsMean | None,
    last_ten: YearsMean | None,
    change: float | None,
    same_value: float | None = None,
) -> list[str]:
    """Return the sentences of a place's record years (spec 7, "Record years"), in order.

    `same_value` is the value every year used shares, when they all share one; then the one
    sentence says so, and nothing is ranked. The window sentence is left out when `change` is
    None, as for fewer than twenty years used. Values carry the variable's units and decimals;
    the change carries its rate units, as a rate does.
    """
    if same_value is not None:
        return [
            _SAME_VALUE_TEMPLATE.format(
                units=entry.units, value=_number_text(same_value, entry.decimals)
            )
        ]
    sentences = [_ranked_sentence(_HIGHEST_TEMPLATE, entry, highest, highest_tied)]
    sentences.append(_ranked_sentence(_LOWEST_TEMPLATE, entry, lowest, lowest_tied))
    if first_ten is not None and last_ten is not None and change is not None:
        sentences.append(_window_sentence(entry, first_ten, last_ten, change))
    return sentences


def season_rate_sentence(
    entry: CatalogueEntry,
    season: Season,
    n_years: int,
    trend: Trend | None,
    kind: VerdictKind,
    has_values: bool = False,
) -> str:
    """Return the sentence of one season's row (spec 7, "All seasons at once").

    `trend` is the season's trend over `n_years` complete years, or None when there are too
    few. `has_values` says the place has complete years of its own, which in a comparison can
    still leave no year in common. Only an assessed trend, which the inference gate allows for
    annual T2M alone, names its verdict `kind`; every other rate says significance was not
    assessed.
    """
    name = SEASON_NAMES[season]
    if trend is None:
        if n_years == 0:
            if has_values:
                return _SEASON_NO_COMMON_YEAR_TEMPLATE.format(season=name)
            return _SEASON_NO_YEAR_TEMPLATE.format(season=name)
        return _SEASON_TOO_FEW_TEMPLATE.format(season=name, years=_complete_years(n_years))
    rate = _SEASON_RATE_TEMPLATE.format(
        season=name,
        amount=_amount(format_signed_rate(trend.sen_slope, entry.decimals), entry.rate_units),
        first_year=trend.first_year,
        last_year=trend.last_year,
        n=trend.n,
    )
    if trend.inference_status == "assessed" and kind in ("significant", "not_significant"):
        words = "significant" if kind == "significant" else "not significant"
        return f"{rate} {_SEASON_ASSESSED_TEMPLATE.format(kind=words)}"
    return f"{rate} {_SEASON_NOT_ASSESSED}"


def overview_sentence(
    entry: CatalogueEntry,
    n_years: int,
    trend: Trend | None,
    kind: VerdictKind,
    highest_year: int | None,
    lowest_year: int | None,
) -> str:
    """Return the sentence of one variable's row on a place's overview (spec 7, "What is
    changing here?").

    `trend` is None when there are too few complete years. `highest_year` and `lowest_year`
    are None when every year has the same value. Only an assessed trend names its verdict
    `kind`; every other rate says significance was not assessed.
    """
    if trend is None:
        if n_years == 0:
            return _OVERVIEW_NO_YEAR
        return _OVERVIEW_TOO_FEW_TEMPLATE.format(years=_complete_years(n_years)).capitalize()
    sentence = _OVERVIEW_RATE_TEMPLATE.format(
        amount=_amount(format_signed_rate(trend.sen_slope, entry.decimals), entry.rate_units),
        total=_amount(format_signed_rate(trend.total_change, entry.decimals), entry.rate_units),
        first_year=trend.first_year,
        last_year=trend.last_year,
        n=trend.n,
    )
    if highest_year is None or lowest_year is None:
        sentence += _OVERVIEW_SAME_VALUE
    else:
        sentence += _OVERVIEW_RECORDS_TEMPLATE.format(highest=highest_year, lowest=lowest_year)
    if trend.inference_status == "assessed" and kind in ("significant", "not_significant"):
        words = "significant" if kind == "significant" else "not significant"
        return f"{sentence}. {_OVERVIEW_ASSESSED_TEMPLATE.format(kind=words)}"
    return f"{sentence}. {_SEASON_NOT_ASSESSED}"


def overview_before_record_sentence(entry: CatalogueEntry) -> str:
    """The row of a variable whose record starts after the requested period ends."""
    return _OVERVIEW_BEFORE_RECORD_TEMPLATE.format(record_start=entry.record_start)


def gap_sentence(
    entry: CatalogueEntry,
    first: str,
    second: str,
    n_years: int,
    trend: Trend | None,
    same_cell: bool,
) -> str:
    """Return the sentence of the gap between two places (spec 7, "The gap between two places").

    `trend` is the descriptive trend of the first place's yearly values minus the second's
    over `n_years` common years, or None when there are too few. Places in the same grid cell
    have the same values, so their gap is zero in every year and says so.
    """
    if n_years == 0:
        return _GAP_NO_YEAR_TEMPLATE.format(first=first, second=second)
    if same_cell:
        return _GAP_SAME_CELL_TEMPLATE.format(first=first, second=second)
    if trend is None:
        return _GAP_TOO_FEW_TEMPLATE.format(first=first, second=second, n=n_years)
    return _GAP_TEMPLATE.format(
        first=first,
        second=second,
        amount=_amount(format_signed_rate(trend.sen_slope, entry.decimals), entry.rate_units),
        first_year=trend.first_year,
        last_year=trend.last_year,
        n=trend.n,
    )


def world_verdict(
    entry: CatalogueEntry, verdict: Verdict, trend: Trend | None, points: int
) -> Verdict:
    """Return the verdict of a world mean (spec 7, "The whole world").

    With a trend the sentence names the sample instead of a grid cell; the kind, which is never
    assessed for a world mean, and the cautions are those of `verdict`. Without a trend the
    verdict is returned as it is.
    """
    if trend is None:
        return verdict
    sentence = _WORLD_TEMPLATE.format(
        variable=_variable_mid_sentence(entry),
        points=points,
        amount=_amount(format_signed_rate(trend.sen_slope, entry.decimals), entry.rate_units),
        first_year=trend.first_year,
        last_year=trend.last_year,
    )
    return verdict.model_copy(update={"sentence": sentence})


def world_sample_note(points: int, step_degrees: int) -> str:
    """The note on how the world sample was drawn and what it describes well."""
    return _WORLD_SAMPLE_NOTE_TEMPLATE.format(points=points, step=step_degrees)


def _ranked_sentence(
    template: str, entry: CatalogueEntry, ranked: Sequence[RecordYear], tied: int
) -> str:
    values = _join(
        [f"{_number_text(item.value, entry.decimals)} in {item.year}" for item in ranked]
    )
    sentence = template.format(units=entry.units, values=values)
    if tied > 0:
        sentence += " " + _tied_sentence(tied, ranked[-1].year)
    return sentence


def _tied_sentence(tied: int, year: int) -> str:
    if tied == 1:
        return _ONE_TIED_TEMPLATE.format(year=year)
    return _MANY_TIED_TEMPLATE.format(n=tied, year=year)


def _window_sentence(
    entry: CatalogueEntry, first_ten: YearsMean, last_ten: YearsMean, change: float
) -> str:
    spans = {
        "last_first": last_ten.years[0],
        "last_last": last_ten.years[-1],
        "first_first": first_ten.years[0],
        "first_last": first_ten.years[-1],
    }
    if change == 0:
        return _WINDOW_SAME_TEMPLATE.format(**spans)
    return _WINDOW_TEMPLATE.format(
        amount=_amount(format_rate(change, entry.decimals), entry.rate_units),
        higher_or_lower="higher" if change > 0 else "lower",
        **spans,
    )


def _number_text(value: float, decimals: int) -> str:
    """A value with the variable's decimals, as Python's format() writes it. A value that is not
    zero but rounds to zero gets more digits, as `format_rate` does, so a small value never
    reads as 0.00 or -0.00.
    """
    if value == 0:
        return f"{0.0:.{decimals}f}"
    precision = decimals
    text = f"{value:.{precision}f}"
    while float(text) == 0 and precision < MAX_SMALL_VALUE_DECIMALS:
        precision += 1
        text = f"{value:.{precision}f}"
    return text


def _complete_years(n_years: int) -> str:
    return "1 complete year" if n_years == 1 else f"{n_years} complete years"


def _variable_mid_sentence(entry: CatalogueEntry) -> str:
    """Return the variable name as it reads inside a sentence: "air temperature"."""
    return entry.name[:1].lower() + entry.name[1:]


def _too_few_years_sentence(n_years: int, variable: str) -> str:
    if n_years == 1:
        return _ONE_YEAR_TEMPLATE.format(variable=variable)
    return _TOO_FEW_YEARS_TEMPLATE.format(n=n_years, variable=variable)


def _kind_and_direction(trend: Trend) -> tuple[VerdictKind, Direction | None]:
    """Apply the verdict rules of spec 7 that need a trend; the first matching row decides."""
    if trend.sen_slope == 0:
        return ("significant" if _is_significant(trend.mk_p) else "not_significant"), None
    direction: Direction = "rising" if trend.sen_slope > 0 else "falling"
    if _is_significant(trend.mk_p):
        return "significant", direction
    return "not_significant", direction


def _is_significant(p: float | None) -> bool:
    return p is not None and p < SIGNIFICANCE_LEVEL


def _trend_sentence(entry: CatalogueEntry, place_name: str, trend: Trend, kind: VerdictKind) -> str:
    fields = {
        "Variable": entry.name,
        "place": place_name,
        "first_year": trend.first_year,
        "last_year": trend.last_year,
    }
    if trend.sen_slope == 0:
        sentence = _ZERO_SLOPE_TEMPLATE.format(**fields)
        if kind == "significant":
            sentence += (
                " The rank-based test meets the stated 5% threshold under its assumptions. "
                "Rank evidence and the median rate are distinct."
            )
        return sentence
    if kind == "significant":
        rate = format_signed_rate(trend.sen_slope, entry.decimals)
        risen_or_fallen = "risen" if trend.sen_slope > 0 else "fallen"
        return _SIGNIFICANT_TEMPLATE.format(
            risen_or_fallen=risen_or_fallen, amount=_amount(rate, entry.rate_units), **fields
        )
    signed_rate = format_signed_rate(trend.sen_slope, entry.decimals)
    return _NOT_SIGNIFICANT_TEMPLATE.format(amount=_amount(signed_rate, entry.rate_units), **fields)


def _amount(rate: str, rate_units: str) -> str:
    """Return "0.25 °C", or the rate alone when the variable has no rate units."""
    return f"{rate} {rate_units}" if rate_units else rate


def _cautions(entry: CatalogueEntry, trend: Trend | None) -> list[Caution]:
    """Return the cautions that apply, most important first (spec 7, "Cautions")."""
    cautions: list[Caution] = []
    if trend is not None and _crossed_source_changes(entry, trend):
        cautions.append("source_change")
    if entry.trend_note:
        cautions.append("variable_note")
    if trend is None:
        return cautions
    if trend.n < SHORT_RECORD_YEARS:
        cautions.append("short_record")
    if trend.lag1 is not None and trend.lag1 >= AUTOCORRELATED_R1:
        cautions.append("autocorrelated")
    if trend.ols_p is not None and _is_significant(trend.mk_p) != _is_significant(trend.ols_p):
        cautions.append("methods_disagree")
    if trend.mk_p is not None and BORDERLINE_P_LOW <= trend.mk_p <= BORDERLINE_P_HIGH:
        cautions.append("borderline")
    return cautions


def _crossed_source_changes(entry: CatalogueEntry, trend: Trend) -> list[int]:
    # Spec 7, "Cautions": the first year used is before the change year and the last
    # year used is on or after it.
    return [year for year in entry.source_changes if trend.first_year < year <= trend.last_year]


def _join(names: Sequence[str]) -> str:
    """Join names as "A", "A and B" or "A, B and C"."""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"
