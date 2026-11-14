"""Day-weighted yearly values, descriptive rates and ordinary MK reference arithmetic.

Pure functions only: no network, no files, no clock, no randomness (spec 7).
"""

import calendar
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats as scipy_stats

from app.models import ScanPoint, Season, Trend
from app.sources.base import MonthKey, MonthlyValues

# Spec 7, step 3: fewer yearly values than this gives the verdict kind "too_few_years".
MIN_YEARS_FOR_TEST = 10
# Spec 7, step 3: fewer yearly values than this adds the "short_record" caution.
SHORT_RECORD_YEARS = 20
# Spec 7, step 6: a trend is significant when p is below this.
SIGNIFICANCE_LEVEL = 0.05
# Spec 7, "Formulas": multiply a per-year slope by this to get a per-decade slope.
PER_DECADE = 10
# Spec 7, "Region view": Benjamini-Hochberg false discovery rate for the map.
FALSE_DISCOVERY_RATE = 0.05
# Spec 7, "Formulas": the normal quantile for the 95% interval, C = 1.96 sqrt(V).
Z_95 = 1.96

# Spec 7, step 2: the months averaged into each year's value, as (year offset, month).
# December of the year before counts toward the following year's DJF value.
SEASON_MONTHS: dict[Season, tuple[tuple[int, int], ...]] = {
    "annual": tuple((0, month) for month in range(1, 13)),
    "DJF": ((-1, 12), (0, 1), (0, 2)),
    "MAM": ((0, 3), (0, 4), (0, 5)),
    "JJA": ((0, 6), (0, 7), (0, 8)),
    "SON": ((0, 9), (0, 10), (0, 11)),
}

# Rounding moves each residual of an exact straight line, a constant included, by about eps
# times the size of the values, so their sum of squares is about eps**2 times x @ x. Residuals
# below this fraction of x @ x, which allows each one a thousand times that rounding, are
# rounding noise: noise has no memory to measure, and its lag-1 autocorrelation could take
# any value. Real variation, however small next to the values, lies far above it.
_ROUNDING_NOISE = (1e3 * sys.float_info.epsilon) ** 2
# r1 is below 1 whenever the residuals are not all zero, so this bounds the reported
# diagnostic against numerical overshoot.
_LARGEST_R1 = math.nextafter(1.0, 0.0)

# Spec 7, "Equal values": the Mann-Kendall test and Sen's slope compare yearly values rounded
# to this many decimals. POWER sends monthly values with 2 decimals, so yearly means that are
# equal in exact arithmetic can differ by rounding alone, about 1e-16 times their size, while
# unequal ones differ by at least 0.01 / 12. Nine decimals lies far from both.
_TIE_DECIMALS = 9
# Spec 7, "Equal values": a Sen's slope smaller than this, in units per year, is zero. When the
# median averages two opposite slopes, rounding leaves a residue near 1e-17 instead of zero.
_ZERO_SEN_SLOPE = 10.0**-_TIE_DECIMALS


def yearly_values(
    monthly: MonthlyValues, season: Season, first_year: int, last_year: int
) -> list[tuple[int, float | None]]:
    """One (year, value) pair per year from `first_year` to `last_year` inclusive (spec 7, step 2).

    The value is the calendar-day-weighted mean of that year's months for `season`,
    in the units of the monthly
    values. A year with any of its months absent or None has the value None, never zero. For
    DJF, the value of year Y averages December of Y - 1 with January and February of Y, so a
    record that starts in 1981 has its first DJF value in 1982.
    """
    return [
        (year, _season_mean(monthly, season, year)) for year in range(first_year, last_year + 1)
    ]


def _season_mean(monthly: MonthlyValues, season: Season, year: int) -> float | None:
    values: list[float] = []
    for offset, month in SEASON_MONTHS[season]:
        value = monthly.get((year + offset, month))
        if value is None:
            return None
        values.append(value)
    weights = [
        calendar.monthrange(year + offset, month)[1] for offset, month in SEASON_MONTHS[season]
    ]
    return math.fsum(value * weight for value, weight in zip(values, weights, strict=True)) / sum(
        weights
    )


@dataclass(frozen=True)
class TrendStats:
    """Spec 7, steps 4 to 8, with every slope per year. `to_trend` converts it for display."""

    n: int
    first_year: int
    last_year: int
    s: int
    var_s: float  # Ordinary tie-adjusted Var(S); not a serial-dependence correction.
    r1: float
    f: float  # Always 1; no residual-lag correction is applied.
    v: float  # V = f Var(S)
    z: float  # Ordinary normal-reference statistic, never used as application inference.
    mk_p: float  # Ordinary two-sided reference p; application inference is separate.
    mk_p_uncorrected: float  # two-sided, from Var(S) alone
    sen_slope: float  # units per year
    sen_ci95: tuple[float, float]  # units per year
    line: tuple[float, float]  # trend-line value in first_year and in last_year
    ols_slope: float  # units per year
    ols_p: float  # Independent-error reference only; never exposed as valid application inference.


def compute_trend(years: Sequence[int], values: Sequence[float]) -> TrendStats:
    """Ordinary MK reference arithmetic, Sen's slope and descriptive OLS quantities.

    Returns spec 7, steps 4 to 8, with slopes in value units per year and every number
    finite. `years` are the years that have a value, ascending and without repeats, and
    `values` the matching yearly values: callers drop missing years first, and a gap between
    years is allowed. Short records are the caller's concern (spec 7, step 3); this needs only
    two values. Raises ValueError when that does not hold. The Mann-Kendall test and Sen's
    slope count values that are equal at `_TIE_DECIMALS` decimals as tied (spec 7, "Equal values").
    """
    t = np.asarray(years, dtype=float)
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n < 2 or len(t) != n or np.any(np.diff(t) <= 0):
        raise ValueError("compute_trend needs two or more values in ascending, distinct years")

    i, j = np.triu_indices(n, k=1)  # every pair i < j
    x_rounded = np.round(x, _TIE_DECIMALS)

    # Spec 7, step 6: the statistic, its variance and the correction.
    s = int(np.sign(x_rounded[j] - x_rounded[i]).sum())
    var_s = _mk_variance(x_rounded)

    # Spec 7, step 5: the memory left in the least-squares residuals.
    fit = scipy_stats.linregress(t, x)
    tc = t - t.mean()
    xc = x - x.mean()
    e = xc - fit.slope * tc  # the residuals, from centred data to limit rounding
    rss = float(e @ e)
    exact_fit = rss <= _ROUNDING_NOISE * float(x @ x)
    r1 = 0.0 if exact_fit else min(float(e[:-1] @ e[1:]) / rss, _LARGEST_R1)
    # Ordinary MK arithmetic is a reference only. Runtime inference is gated separately.
    # Residual autocorrelation is diagnostic, never a universal variance correction.
    f = 1.0
    v = f * var_s
    z = _mk_z(s, v)

    # Spec 7, steps 4 and 7: Sen's slope against the real years, the interval and the line.
    slopes = np.sort((x_rounded[j] - x_rounded[i]) / (t[j] - t[i]))
    sen_slope = float(np.median(slopes))
    if abs(sen_slope) < _ZERO_SEN_SLOPE:
        sen_slope = 0.0
    t_median = float(np.median(t))
    x_median = float(np.median(x))

    # Spec 7, step 8: the least-squares slope's t-test, standard error multiplied by sqrt(f).
    ols_slope = float(fit.slope)
    if exact_fit:
        # Spec 7, "Exact straight lines": the values decide whether the line is flat, since
        # rounding can leave linregress a slope of about 1e-32 for equal values, as it does
        # when the years have gaps.
        is_flat = bool(np.ptp(x_rounded) == 0)
        ols_slope = 0.0 if is_flat else ols_slope
        ols_p = 1.0 if is_flat else 0.0
    else:
        standard_error = math.sqrt(rss / (n - 2) / float(tc @ tc)) * math.sqrt(f)
        ols_p = float(2 * scipy_stats.t.sf(abs(ols_slope / standard_error), n - 2))

    return TrendStats(
        n=n,
        first_year=int(years[0]),
        last_year=int(years[-1]),
        s=s,
        var_s=var_s,
        r1=r1,
        f=f,
        v=v,
        z=z,
        mk_p=_two_sided_p(z),
        mk_p_uncorrected=_two_sided_p(_mk_z(s, var_s)),
        sen_slope=sen_slope,
        sen_ci95=_sen_interval(slopes, v),
        line=(
            x_median + sen_slope * (float(t[0]) - t_median),
            x_median + sen_slope * (float(t[-1]) - t_median),
        ),
        ols_slope=ols_slope,
        ols_p=ols_p,
    )


def _mk_variance(x: np.ndarray) -> float:
    # Spec 7, "Formulas": n (n - 1) (2n + 5) / 18, less t (t - 1) (2t + 5) / 18 per tie group.
    # A value that is not tied is a group of one and subtracts nothing.
    n = len(x)
    _, group_sizes = np.unique(x, return_counts=True)
    ties = sum(int(t) * (int(t) - 1) * (2 * int(t) + 5) for t in group_sizes)
    return (n * (n - 1) * (2 * n + 5) - ties) / 18


def _mk_z(s: int, v: float) -> float:
    # Spec 7, "Formulas". V is zero only when every value is tied, and then S is zero too.
    if s > 0:
        return (s - 1) / math.sqrt(v)
    if s < 0:
        return (s + 1) / math.sqrt(v)
    return 0.0


def _two_sided_p(z: float) -> float:
    # 2 (1 - Phi(|Z|)) equals erfc(|Z| / sqrt(2)), which keeps precision for large |Z|.
    return math.erfc(abs(z) / math.sqrt(2))


def _sen_interval(slopes: np.ndarray, v: float) -> tuple[float, float]:
    # Spec 7, "Formulas": slope numbers count the sorted slopes from 1.
    N = len(slopes)
    C = Z_95 * math.sqrt(v)
    lower = _clamp_rank(math.floor((N - C) / 2), N)
    upper = _clamp_rank(math.ceil((N + C) / 2 + 1), N)
    return float(slopes[lower - 1]), float(slopes[upper - 1])


def _clamp_rank(rank: int, N: int) -> int:
    return min(max(rank, 1), N)


def to_trend(stats: TrendStats, scan: list[ScanPoint] | None = None) -> Trend:
    """The Trend of spec 5, with Sen's slope, its interval and the least-squares slope per decade.

    `total_change` is the per-decade Sen's slope times the decades from `first_year` to
    `last_year`, in value units. `line` stays in value units. `scan` is passed through.
    """
    sen_slope = stats.sen_slope * PER_DECADE
    return Trend(
        n=stats.n,
        first_year=stats.first_year,
        last_year=stats.last_year,
        sen_slope=sen_slope,
        sen_ci95=None,
        line=stats.line,
        total_change=sen_slope * (stats.last_year - stats.first_year) / PER_DECADE,
        mk_p=None,
        lag1=stats.r1,
        variance_factor=stats.f,
        ols_slope=stats.ols_slope * PER_DECADE,
        ols_p=None,
        inference_reason=(
            "Reference arithmetic only; no validated inference policy has been applied."
        ),
        scan=scan,
    )


def period_scan(years: Sequence[int], values: Sequence[float]) -> list[ScanPoint]:
    """Spec 7, step 10: the same test repeated from each later start year.

    `years` and `values` follow the rules of `compute_trend`: years with a value only,
    ascending. There is one point per start year among `years` that leaves at least
    MIN_YEARS_FOR_TEST values, in start order, with Sen's slope per decade and the unavailable
    p-value; scanning is descriptive. A record shorter than that gives an empty list.
    """
    points: list[ScanPoint] = []
    for k in range(len(years) - MIN_YEARS_FOR_TEST + 1):
        tail = compute_trend(years[k:], values[k:])
        points.append(ScanPoint(start=years[k], sen_slope=tail.sen_slope * PER_DECADE, mk_p=None))
    return points


def benjamini_hochberg(p_values: Sequence[float], q: float = FALSE_DISCOVERY_RATE) -> list[bool]:
    """Which p-values pass the Benjamini-Hochberg step-up test at false discovery rate `q`.

    Returns one flag per p-value, in the input order (spec 7, "Region view"). Cells without a
    result are left out by the caller, so every p-value here is a number. An empty input gives
    an empty list.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda index: p_values[index])
    # The largest rank k whose p-value is at most k q / m; every smaller p-value passes too.
    passing = 0
    for k, index in enumerate(order, start=1):
        if p_values[index] <= k * q / m:
            passing = k
    significant = [False] * m
    for index in order[:passing]:
        significant[index] = True
    return significant


def cos_lat_weighted_mean(
    cells: Sequence[tuple[float, MonthlyValues]],
) -> dict[MonthKey, float | None]:
    """The area mean of grid cells for each month, weighting each cell by cos(latitude).

    `cells` pairs each cell's latitude in degrees with its monthly values (spec 7, "Region
    view"). For each month any cell has, in month order, the result is the weighted mean of
    the cells that have a value that month, in the cells' units; a missing value is left out,
    never counted as zero. A month in which no cell has a value is None.
    """
    months = sorted({month for _, monthly in cells for month in monthly})
    return {month: _weighted_mean(cells, month) for month in months}


def _weighted_mean(cells: Sequence[tuple[float, MonthlyValues]], month: MonthKey) -> float | None:
    # Keep the spatial footprint fixed; a changing denominator can create an apparent trend.
    if any(monthly.get(month) is None for _, monthly in cells):
        return None
    present = [
        (math.cos(math.radians(lat)), value)
        for lat, monthly in cells
        if (value := monthly.get(month)) is not None
    ]
    if not present:
        return None
    return math.fsum(w * value for w, value in present) / math.fsum(w for w, _ in present)
