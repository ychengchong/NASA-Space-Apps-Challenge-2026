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
