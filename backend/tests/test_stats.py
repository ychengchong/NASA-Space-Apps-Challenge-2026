"""Spec 7 statistics: the worked fixtures, the reference check, seeded noise and edge cases."""

import math
from collections.abc import Sequence
from dataclasses import astuple, dataclass

import numpy as np
import pymannkendall
import pytest
from scipy import stats as scipy_stats

from app.catalogue import get_entry
from app.sources.base import MonthKey
from app.stats import (
    MIN_YEARS_FOR_TEST,
    PER_DECADE,
    SIGNIFICANCE_LEVEL,
    benjamini_hochberg,
    compute_trend,
    cos_lat_weighted_mean,
    period_scan,
    to_trend,
    yearly_values,
)
from app.verdict import build_verdict


@dataclass(frozen=True)
class Fixture:
    """A worked fixture of spec 7, with the expected numbers written as the table prints them."""

    years: tuple[int, ...]
    values: tuple[float, ...]
    s: int
    var_s: str
    r1: str
    f: str
    z: str
    p: str
    sen_slope: str
    sen_ci95: tuple[str, str]
    line: tuple[str, str]
    significant: bool


FIXTURE_A = Fixture(
    years=tuple(range(2001, 2011)),
    values=(2, 4, 3, 5, 7, 6, 8, 9, 11, 10),
    s=39,
    var_s="125",
    r1="-0.499",
    f="1",
    z="3.399",
    p="0.00068",
    sen_slope="1.0",
    sen_ci95=("0.667", "1.25"),
    line=("2.0", "11.0"),
    significant=True,
)

FIXTURE_B = Fixture(
    years=tuple(range(2001, 2013)),
    values=(1, 3, 4, 5, 4.5, 3.5, 2.5, 5.5, 7, 8, 7.5, 6.5),
    s=40,
    var_s="212.667",
    r1="0.349",
    f="2.074",
    z="1.857",
    p="0.0633",
    sen_slope="0.5",
    sen_ci95=("-0.167", "1.0"),
    line=("2.0", "7.5"),
    significant=False,
)

# Spec 7, "Worked fixtures": fixture B would pass the uncorrected test with this p-value.
FIXTURE_B_UNCORRECTED_P = "0.0075"

both_fixtures = pytest.mark.parametrize("fixture", [FIXTURE_A, FIXTURE_B], ids=["A", "B"])

# Fixture A shrunk to a ten-millionth and set on a large offset: real variation that is tiny
# next to the values, far above rounding.
LARGE_OFFSET_SMALL_NOISE = tuple(100.0 + 1e-7 * value for value in FIXTURE_A.values)

# Two JJA seasons whose means are both 0.2 in exact arithmetic. As floats, (0.1 + 0.2 + 0.3) / 3
# and (0.2 + 0.2 + 0.2) / 3 differ in the last bit.
EQUAL_MEANS_MONTHS = ((0.1, 0.2, 0.3), (0.2, 0.2, 0.2))

# Two-decimal yearly values for 2000 to 2011 whose two middle pairwise slopes are exactly
# -1/700 and +1/700, so the exact Sen's slope is zero but their float mean is not.
CANCELLING_MIDDLE_SLOPES = (0.15, 0.24, 0.27, 0.28, 0.12, 0.29, 0.26, 0.14, 0.25, 0.17, 0.1, 0.3)

# Years with gaps, whose mean has no exact binary form.
YEARS_WITH_GAPS = (1981, 1982, 1985, 1990, 1991, 1993, 1999, 2004, 2010, 2017, 2018, 2023)

# Spec 12, "Testing and validation": the seeded noise test.
NOISE_SEED = 20261114
NOISE_SERIES = 2000
NOISE_LENGTH = 45
NOISE_MIN_RATE = 0.03
NOISE_MAX_RATE = 0.07


def assert_matches_printed(actual: float, printed: str) -> None:
    """Pass when `actual` rounds to `printed`: within half a unit of its last printed digit."""
    decimals = len(printed.partition(".")[2])
    assert actual == pytest.approx(float(printed), abs=0.5 * 10**-decimals)


def every_month(first_year: int, last_year: int, value: float) -> dict[MonthKey, float | None]:
    return {
        (year, month): value for year in range(first_year, last_year + 1) for month in range(1, 13)
    }


def jja_means(seasons: Sequence[tuple[float, float, float]], first_year: int) -> list[float]:
    """The JJA yearly values of consecutive years from `first_year`, one per season of months."""
    monthly: dict[MonthKey, float | None] = {
        (first_year + k, month): value
        for k, months in enumerate(seasons)
        for month, value in zip((6, 7, 8), months, strict=True)
    }
    last_year = first_year + len(seasons) - 1
    return [
        value
        for _, value in yearly_values(monthly, "JJA", first_year, last_year)
        if value is not None
    ]


# Worked fixtures (spec 7)


@both_fixtures
def test_fixture_mann_kendall_statistic(fixture: Fixture) -> None:
    assert compute_trend(fixture.years, fixture.values).s == fixture.s


@both_fixtures
def test_fixture_variance_before_correction(fixture: Fixture) -> None:
    assert_matches_printed(compute_trend(fixture.years, fixture.values).var_s, fixture.var_s)


@both_fixtures
def test_fixture_lag1_autocorrelation_of_residuals(fixture: Fixture) -> None:
    assert_matches_printed(compute_trend(fixture.years, fixture.values).r1, fixture.r1)


@both_fixtures
def test_fixture_correction_factor(fixture: Fixture) -> None:
    assert_matches_printed(compute_trend(fixture.years, fixture.values).f, fixture.f)


@both_fixtures
def test_fixture_test_statistic_after_correction(fixture: Fixture) -> None:
    assert_matches_printed(compute_trend(fixture.years, fixture.values).z, fixture.z)


@both_fixtures
def test_fixture_p_value_after_correction(fixture: Fixture) -> None:
    assert_matches_printed(compute_trend(fixture.years, fixture.values).mk_p, fixture.p)


@both_fixtures
def test_fixture_sen_slope_per_year(fixture: Fixture) -> None:
    assert_matches_printed(
        compute_trend(fixture.years, fixture.values).sen_slope, fixture.sen_slope
    )


@both_fixtures
def test_fixture_sen_interval_per_year(fixture: Fixture) -> None:
    lower, upper = compute_trend(fixture.years, fixture.values).sen_ci95
    assert_matches_printed(lower, fixture.sen_ci95[0])
    assert_matches_printed(upper, fixture.sen_ci95[1])


@both_fixtures
def test_fixture_trend_line_in_first_and_last_year(fixture: Fixture) -> None:
    first, last = compute_trend(fixture.years, fixture.values).line
    assert_matches_printed(first, fixture.line[0])
    assert_matches_printed(last, fixture.line[1])


@both_fixtures
def test_fixture_significance_at_five_percent(fixture: Fixture) -> None:
    stats = compute_trend(fixture.years, fixture.values)
    assert (stats.mk_p < SIGNIFICANCE_LEVEL) is fixture.significant


@pytest.mark.parametrize(
    ("fixture", "kind"),
    [(FIXTURE_A, "significant"), (FIXTURE_B, "not_significant")],
    ids=["A", "B"],
)
def test_fixture_verdict_kind_and_direction(fixture: Fixture, kind: str) -> None:
    trend = to_trend(compute_trend(fixture.years, fixture.values))
    verdict = build_verdict(get_entry("air_temp"), "X", len(fixture.values), trend)
    assert (verdict.kind, verdict.direction) == (kind, "rising")


def test_fixture_b_passes_the_uncorrected_test() -> None:
    stats = compute_trend(FIXTURE_B.years, FIXTURE_B.values)
    assert_matches_printed(stats.mk_p_uncorrected, FIXTURE_B_UNCORRECTED_P)


def test_negative_r1_leaves_the_variance_uncorrected() -> None:
    stats = compute_trend(FIXTURE_A.years, FIXTURE_A.values)
    assert stats.r1 < 0
    assert stats.f == 1
    assert stats.v == stats.var_s


# Reference check against pymannkendall (spec 12)


@both_fixtures
def test_uncorrected_p_matches_pymannkendall(fixture: Fixture) -> None:
    reference = pymannkendall.original_test(np.array(fixture.values, dtype=float))
    stats = compute_trend(fixture.years, fixture.values)
    assert stats.mk_p_uncorrected == pytest.approx(reference.p, rel=1e-9)


@both_fixtures
def test_sen_slope_matches_pymannkendall(fixture: Fixture) -> None:
    reference = pymannkendall.original_test(np.array(fixture.values, dtype=float))
    stats = compute_trend(fixture.years, fixture.values)
    assert stats.sen_slope == pytest.approx(reference.slope, rel=1e-12)


# Seeded noise (spec 12)


def test_corrected_test_rarely_finds_a_trend_in_pure_noise() -> None:
    rng = np.random.default_rng(NOISE_SEED)
    series = rng.standard_normal((NOISE_SERIES, NOISE_LENGTH))
    years = list(range(1981, 1981 + NOISE_LENGTH))
    significant = sum(
        compute_trend(years, values.tolist()).mk_p < SIGNIFICANCE_LEVEL for values in series
    )
    assert NOISE_MIN_RATE <= significant / NOISE_SERIES <= NOISE_MAX_RATE


# Yearly values (spec 7, step 2)


def test_yearly_values_give_one_entry_per_year_inclusive() -> None:
    years = [year for year, _ in yearly_values({}, "annual", 2001, 2005)]
    assert years == [2001, 2002, 2003, 2004, 2005]


def test_annual_value_is_the_mean_of_twelve_months() -> None:
    monthly = {(2000, month): float(month) for month in range(1, 13)}
    assert yearly_values(monthly, "annual", 2000, 2000) == [(2000, 6.5)]


def test_season_value_is_the_mean_of_its_three_months() -> None:
    monthly = {(2000, month): float(month) for month in range(1, 13)}
    assert yearly_values(monthly, "JJA", 2000, 2000) == [(2000, 7.0)]


def test_december_counts_toward_following_year() -> None:
    monthly = {(1999, 12): 1.0, (2000, 1): 2.0, (2000, 2): 6.0, (2000, 12): 100.0}
    assert yearly_values(monthly, "DJF", 2000, 2000) == [(2000, 3.0)]


def test_first_djf_value_is_the_year_after_the_record_starts() -> None:
    monthly = every_month(1981, 1983, 1.0)
    assert yearly_values(monthly, "DJF", 1981, 1983) == [(1981, None), (1982, 1.0), (1983, 1.0)]


def test_year_with_a_none_month_has_no_value() -> None:
    monthly = every_month(2000, 2000, 1.0)
    monthly[(2000, 5)] = None
    assert yearly_values(monthly, "annual", 2000, 2000) == [(2000, None)]


def test_year_with_an_absent_month_has_no_value() -> None:
    monthly = every_month(2000, 2000, 1.0)
    del monthly[(2000, 5)]
    assert yearly_values(monthly, "annual", 2000, 2000) == [(2000, None)]


# Edge cases of the trend (spec 7, steps 4 to 8)


def test_constant_values_have_zero_sen_slope() -> None:
    assert compute_trend(range(2001, 2013), [5.0] * 12).sen_slope == 0


def test_constant_values_give_p_value_one() -> None:
    stats = compute_trend(range(2001, 2013), [5.0] * 12)
    assert (stats.v, stats.z, stats.mk_p, stats.ols_p) == (0, 0, 1, 1)


def test_constant_values_in_years_with_gaps_give_p_value_one() -> None:
    stats = compute_trend(YEARS_WITH_GAPS, [0.1] * len(YEARS_WITH_GAPS))
    assert (stats.mk_p, stats.ols_p) == (1, 1)


def test_constant_values_in_years_with_gaps_have_zero_least_squares_slope() -> None:
    assert compute_trend(YEARS_WITH_GAPS, [0.1] * len(YEARS_WITH_GAPS)).ols_slope == 0


def test_equal_means_from_different_months_add_nothing_to_s() -> None:
    assert compute_trend([2001, 2002], jja_means(EQUAL_MEANS_MONTHS, 2001)).s == 0


def test_equal_means_from_different_months_form_one_tie_group() -> None:
    # Eight distinct values and one tied pair: 125 - 2 (2 - 1) (2 * 2 + 5) / 18 = 124.
    distinct = [(value,) * 3 for value in (0.1, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]
    values = jja_means([*distinct[:4], *EQUAL_MEANS_MONTHS, *distinct[4:]], 2001)
    assert compute_trend(range(2001, 2011), values).var_s == 124


def test_equal_means_from_different_months_have_zero_sen_slope() -> None:
    assert compute_trend([2001, 2002], jja_means(EQUAL_MEANS_MONTHS, 2001)).sen_slope == 0


def test_equal_means_from_different_months_give_p_value_one() -> None:
    assert compute_trend([2001, 2002], jja_means(EQUAL_MEANS_MONTHS, 2001)).ols_p == 1


def test_sen_slope_is_zero_when_the_middle_slopes_cancel() -> None:
    assert compute_trend(range(2000, 2012), CANCELLING_MIDDLE_SLOPES).sen_slope == 0


def test_cancelling_middle_slopes_get_the_zero_slope_verdict() -> None:
    trend = to_trend(compute_trend(range(2000, 2012), CANCELLING_MIDDLE_SLOPES))
    verdict = build_verdict(get_entry("air_temp"), "X", len(CANCELLING_MIDDLE_SLOPES), trend)
    assert (verdict.direction, verdict.sentence) == (
        None,
        "Air temperature in X shows no upward or downward trend from 2000 to 2011.",
    )


def test_constant_values_show_no_memory() -> None:
    # 0.1 has no exact binary form, so the residuals are rounding noise rather than zero.
    assert compute_trend(range(1981, 2026), [0.1] * 45).r1 == 0


def test_exact_straight_line_shows_no_memory() -> None:
    values = [3 + 0.1 * k for k in range(45)]
    assert compute_trend(range(1981, 2026), values).r1 == 0


def test_small_noise_on_a_large_offset_keeps_its_memory() -> None:
    # Shifting and scaling fixture A leaves its r1 unchanged.
    stats = compute_trend(FIXTURE_A.years, LARGE_OFFSET_SMALL_NOISE)
    assert_matches_printed(stats.r1, FIXTURE_A.r1)


def test_small_noise_on_a_large_offset_keeps_the_t_test() -> None:
    # Fixture A has a negative r1, so f is 1 and the p-value is linregress's own.
    stats = compute_trend(FIXTURE_A.years, LARGE_OFFSET_SMALL_NOISE)
    reference = scipy_stats.linregress(FIXTURE_A.years, LARGE_OFFSET_SMALL_NOISE)
    assert stats.ols_p == pytest.approx(reference.pvalue, rel=1e-6)


def test_two_values_give_only_finite_numbers() -> None:
    stats = compute_trend([2001, 2002], [1.0, 3.0])
    numbers = [number for item in astuple(stats) for number in np.ravel(item)]
    assert all(math.isfinite(number) for number in numbers)


def test_tied_values_reduce_the_variance() -> None:
    # One pair of tied values: 125 - 2 (2 - 1) (2 * 2 + 5) / 18 = 124.
    stats = compute_trend(range(2001, 2011), [1, 2, 3, 4, 5, 5, 7, 8, 9, 10])
    assert stats.var_s == 124


def test_gap_in_years_does_not_distort_sen_slope() -> None:
    years = [2001, 2002, 2003, 2010, 2011, 2012]
    values = [0.5 * (year - 2001) for year in years]
    assert compute_trend(years, values).sen_slope == 0.5


def test_years_out_of_order_are_rejected() -> None:
    with pytest.raises(ValueError):
        compute_trend([2002, 2001, 2003], [1.0, 2.0, 3.0])


def test_ols_p_is_the_plain_t_test_when_f_is_one() -> None:
    stats = compute_trend(FIXTURE_A.years, FIXTURE_A.values)
    reference = scipy_stats.linregress(FIXTURE_A.years, FIXTURE_A.values)
    assert stats.ols_p == pytest.approx(reference.pvalue, rel=1e-9)


def test_ols_standard_error_is_multiplied_by_sqrt_f() -> None:
    stats = compute_trend(FIXTURE_B.years, FIXTURE_B.values)
    reference = scipy_stats.linregress(FIXTURE_B.years, FIXTURE_B.values)
    t_statistic = reference.slope / (reference.stderr * math.sqrt(stats.f))
    expected = 2 * scipy_stats.t.sf(abs(t_statistic), stats.n - 2)
    assert stats.ols_p == pytest.approx(expected, rel=1e-9)


# Conversion to the Trend type (spec 5)


def test_trend_gives_slopes_per_decade() -> None:
    stats = compute_trend(FIXTURE_B.years, FIXTURE_B.values)
    trend = to_trend(stats)
    assert trend.sen_slope == stats.sen_slope * PER_DECADE
    assert trend.sen_ci95 == (stats.sen_ci95[0] * PER_DECADE, stats.sen_ci95[1] * PER_DECADE)
    assert trend.ols_slope == stats.ols_slope * PER_DECADE


def test_trend_total_change_spans_the_years_used() -> None:
    # Fixture B: 0.5 per year over the 11 years from 2001 to 2012.
    trend = to_trend(compute_trend(FIXTURE_B.years, FIXTURE_B.values))
    assert trend.total_change == pytest.approx(5.5)


def test_trend_reports_memory_and_correction() -> None:
    stats = compute_trend(FIXTURE_B.years, FIXTURE_B.values)
    trend = to_trend(stats)
    assert (trend.lag1, trend.variance_factor, trend.mk_p) == (stats.r1, stats.f, stats.mk_p)


def test_trend_line_stays_in_value_units() -> None:
    stats = compute_trend(FIXTURE_B.years, FIXTURE_B.values)
    assert to_trend(stats).line == stats.line


# Period scan (spec 7, step 10)


def test_scan_starts_leave_at_least_ten_values() -> None:
    years = list(range(2001, 2016))
    scan = period_scan(years, [float(year % 7) for year in years])
    assert [point.start for point in scan] == [2001, 2002, 2003, 2004, 2005, 2006]


def test_scan_starts_only_in_years_that_have_a_value() -> None:
    years = [2001, 2003, *range(2005, 2015)]
    scan = period_scan(years, [float(year % 7) for year in years])
    assert [point.start for point in scan] == [2001, 2003, 2005]


def test_scan_point_matches_the_trend_of_its_tail() -> None:
    years = list(range(2001, 2016))
    values = [float(year % 7) for year in years]
    point = period_scan(years, values)[2]
    tail = compute_trend(years[2:], values[2:])
    assert (point.sen_slope, point.mk_p) == (tail.sen_slope * PER_DECADE, tail.mk_p)


def test_scan_of_a_short_record_is_empty() -> None:
    years = list(range(2001, 2001 + MIN_YEARS_FOR_TEST - 1))
    assert period_scan(years, [float(year) for year in years]) == []


# Region view (spec 7)


def test_benjamini_hochberg_steps_up_past_a_failing_rank() -> None:
    # Ranked thresholds are 0.0125, 0.025, 0.0375 and 0.05. 0.03 misses its own (0.025),
    # but 0.035 meets rank 3, so every p-value up to rank 3 passes.
    assert benjamini_hochberg([0.03, 0.001, 0.035, 0.3]) == [True, True, True, False]


def test_benjamini_hochberg_is_stricter_than_the_plain_threshold() -> None:
    assert benjamini_hochberg([0.04, 0.3, 0.5, 0.6]) == [False, False, False, False]


def test_benjamini_hochberg_of_no_p_values_is_empty() -> None:
    assert benjamini_hochberg([]) == []


def test_weighted_mean_weights_cells_by_cos_latitude() -> None:
    # cos 0° = 1 and cos 60° = 0.5, so (1 * 10 + 0.5 * 40) / 1.5 = 20.
    cells = [(0.0, {(2000, 1): 10.0}), (60.0, {(2000, 1): 40.0})]
    assert cos_lat_weighted_mean(cells)[(2000, 1)] == pytest.approx(20.0)


def test_weighted_mean_leaves_out_a_cell_without_a_value() -> None:
    cells = [(0.0, {(2000, 1): 10.0}), (60.0, {(2000, 1): None})]
    assert cos_lat_weighted_mean(cells)[(2000, 1)] == 10.0


def test_weighted_mean_is_none_when_no_cell_has_a_value() -> None:
    cells = [(0.0, {(2000, 1): None}), (60.0, {})]
    assert cos_lat_weighted_mean(cells) == {(2000, 1): None}
