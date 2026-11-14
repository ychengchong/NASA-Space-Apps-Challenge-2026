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
    Trend,
    Verdict,
    VerdictKind,
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
    "{Variable} in {place} has {risen_or_fallen} by about {amount} per decade "
    "from {first_year} to {last_year}. This trend is statistically significant."
)
_NOT_SIGNIFICANT_TEMPLATE = (
    "{Variable} in {place} changed by about {amount} per decade from {first_year} to "
    "{last_year}. Year-to-year variation alone could produce a change this size, "
    "so the trend is not statistically significant."
)
_ZERO_SLOPE_TEMPLATE = (
    "{Variable} in {place} shows no upward or downward trend from {first_year} to {last_year}."
)
_TOO_FEW_YEARS_TEMPLATE = (
    "There are only {n} complete years of {variable} data here. "
    "That is too few to test for a trend."
)
_ONE_YEAR_TEMPLATE = (
    "There is only 1 complete year of {variable} data here. That is too few to test for a trend."
)
_NO_DATA_TEMPLATE = "There is no {variable} data for this location."

# Spec 7, "Cautions": what the user reads.
_SOURCE_CHANGE_TEMPLATE = (
    "The data source for this variable changes in {years}, which can create an artificial step."
)
_FIXED_CAUTION_TEXTS: dict[Caution, str] = {
    "short_record": (
        "This record is short. Trends in short records often fade as more years arrive."
    ),
    "autocorrelated": (
        "Each year here resembles the one before. "
        "The test allows for that, which makes it harder to pass."
    ),
    "methods_disagree": "Two standard methods disagree about this trend.",
    "borderline": "This result is close to the threshold for significance.",
}

# Spec 7, "Comparing places".
_OPPOSITE_TEMPLATE = (
    "{Variable} is rising significantly in {rising_places} "
    "and falling significantly in {falling_places} over the same years."
)
_SAME_DIRECTION_TEMPLATE = "{Variable} is {direction} significantly in all {k} places."
# With exactly this many places, the summary reads "both places" instead of "all {k} places".
BOTH_PLACES_COUNT = 2
_SAME_DIRECTION_BOTH_TEMPLATE = "{Variable} is {direction} significantly in both places."
_UNCLEAR_TEMPLATE = (
    "{Variable} does not show a significant trend in every place, "
    "so the places cannot be clearly contrasted."
)


def format_rate(rate_per_decade: float, decimals: int) -> str:
    """Return the size of a rate per decade as text, without a sign (spec 7, `{rate}`).

    The size is rounded to `decimals` digits. If that rounds to zero, one more digit is
    shown, so 0.004 with 2 decimals reads "0.004". Rounding is that of Python's format(), which
    the frontend's formatRate copies so the screen and the sentence show the same digits: a
    value exactly halfway rounds to the even digit, so 0.125 with 2 decimals reads "0.12".
    """
    size = abs(rate_per_decade)
    text = f"{size:.{decimals}f}"
    if float(text) == 0:
        return f"{size:.{decimals + 1}f}"
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
    rising = _significant_place_names(results, "rising")
    falling = _significant_place_names(results, "falling")
    if rising and falling:
        return "opposite_directions", _OPPOSITE_TEMPLATE.format(
            Variable=entry.name, rising_places=_join(rising), falling_places=_join(falling)
        )
    if len(rising) == len(results) or len(falling) == len(results):
        direction: Direction = "rising" if rising else "falling"
        template = (
            _SAME_DIRECTION_BOTH_TEMPLATE
            if len(results) == BOTH_PLACES_COUNT
            else _SAME_DIRECTION_TEMPLATE
        )
        return "same_direction", template.format(
            Variable=entry.name, direction=direction, k=len(results)
        )
    return "unclear", _UNCLEAR_TEMPLATE.format(Variable=entry.name)


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
        return "not_significant", None
    direction: Direction = "rising" if trend.sen_slope > 0 else "falling"
    if _is_significant(trend.mk_p):
        return "significant", direction
    return "not_significant", direction


def _is_significant(p: float) -> bool:
    return p < SIGNIFICANCE_LEVEL


def _trend_sentence(entry: CatalogueEntry, place_name: str, trend: Trend, kind: VerdictKind) -> str:
    fields = {
        "Variable": entry.name,
        "place": place_name,
        "first_year": trend.first_year,
        "last_year": trend.last_year,
    }
    if trend.sen_slope == 0:
        return _ZERO_SLOPE_TEMPLATE.format(**fields)
    if kind == "significant":
        rate = format_rate(trend.sen_slope, entry.decimals)
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
    if trend.lag1 >= AUTOCORRELATED_R1:
        cautions.append("autocorrelated")
    if _is_significant(trend.mk_p) != _is_significant(trend.ols_p):
        cautions.append("methods_disagree")
    if BORDERLINE_P_LOW <= trend.mk_p <= BORDERLINE_P_HIGH:
        cautions.append("borderline")
    return cautions


def _crossed_source_changes(entry: CatalogueEntry, trend: Trend) -> list[int]:
    # Spec 7, "Cautions": the first year used is before the change year and the last
    # year used is on or after it.
    return [year for year in entry.source_changes if trend.first_year < year <= trend.last_year]


def _significant_place_names(results: Sequence[PlaceResult], direction: Direction) -> list[str]:
    return [
        result.place.name
        for result in results
        if result.verdict.kind == "significant" and result.verdict.direction == direction
    ]


def _join(names: Sequence[str]) -> str:
    """Join names as "A", "A and B" or "A, B and C"."""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"
