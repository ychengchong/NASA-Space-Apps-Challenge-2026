"""Frozen Monte Carlo MK inference and the shared tools' application eligibility policy.

File loading happens here; stats.py remains pure. Missing/corrupt calibration fails closed.
"""

import hashlib
import json
from collections.abc import Sequence
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import TypedDict, cast

import numpy as np

from app.catalogue import CatalogueEntry
from app.config import DATA_DIR
from app.models import Season, Trend
from app.stats import MIN_YEARS_FOR_TEST, compute_trend, to_trend

ANALYSIS_VERSION = "td-2026-11-v1"
METHOD_ID = "mk_mc_envelope_v1"
TABLE_SHA256 = "c79203b7cc8c74a2199e1b505a756735c74929840427ec46a1d76013faf47fdf"
MIN_INFERENCE_YEARS = 20
MAX_INFERENCE_YEARS = 45
ASSUMPTIONS = (
    "Conservative Monte Carlo MK test; calibrated for stationary AR(1) noise with "
    "correlation 0, 0.2 or 0.5 and Gaussian or centered exponential innovations. "
    "Other dependence, structural changes and distributions are not validated. "
    "A significant result does not establish causation."
)


class CalibrationTable(TypedDict):
    replicates: int
    tails: dict[str, list[int]]


@lru_cache(maxsize=1)
def load_table(path: Path = DATA_DIR / "inference-v1.json") -> CalibrationTable | None:
    """Load the exact approved table; return None rather than infer from unknown bytes."""
    try:
        content = path.read_bytes()
    except OSError:
        return None
    if hashlib.sha256(content).hexdigest() != TABLE_SHA256:
        return None
    return cast(CalibrationTable, json.loads(content))


def calibrated_p(years: Sequence[int], values: Sequence[float]) -> float | None:
    """Two-sided conservative null-envelope p; unavailable outside the frozen length range."""
    table = load_table()
    if table is None or not MIN_INFERENCE_YEARS <= len(values) <= MAX_INFERENCE_YEARS:
        return None
    x = np.round(np.asarray(values, dtype=float), 9)
    i, j = np.triu_indices(len(x), 1)
    score = abs(int(np.sign(x[j] - x[i]).sum()))
    return (table["tails"][str(len(x))][score] + 1) / (table["replicates"] + 1)


def analyse_values(
    years: list[int],
    values: list[float],
    entry: CatalogueEntry,
    season: Season,
    *,
    allow_inference: bool = True,
    complete_period: bool = True,
) -> Trend | None:
    """Descriptive rates from real years; p only for an eligible, calibrated annual T2M case.

    No rate is returned with fewer than ten complete values. Confidence intervals and OLS
    significance are not validated for serial dependence and always remain null.
    """
    if len(values) < MIN_YEARS_FOR_TEST:
        return None
    trend = to_trend(compute_trend(years, values), None)
    reason = None
    if len(values) < MIN_INFERENCE_YEARS:
        reason = "Formal inference requires at least 20 complete annual values."
    elif not complete_period or any(right - left != 1 for left, right in pairwise(years)):
        reason = "Missing years: confirm a fully covered contiguous subperiod."
    elif any(years[0] < transition <= years[-1] for transition in entry.source_changes):
        reason = "The period crosses a source transition; confirm a homogeneous subperiod."
    elif entry.id != "air_temp" or season != "annual" or not allow_inference:
        reason = (
            "Inference is validated only for individual annual T2M series; "
            "this case is descriptive."
        )
    elif len(values) > MAX_INFERENCE_YEARS:
        reason = "The record length is outside the calibrated 20-45 year range."
    p = calibrated_p(years, values) if reason is None else None
    if reason is None and p is None:
        reason = "The approved calibration table is unavailable or failed integrity verification."
    return trend.model_copy(
        update={
            "mk_p": p,
            "sen_ci95": None,
            "ols_p": None,
            "inference_status": "assessed" if p is not None else "unavailable",
            "inference_reason": reason,
            "method_id": METHOD_ID if p is not None else None,
            "ci_method": None,
            "assumptions": ASSUMPTIONS if p is not None else None,
            "variance_factor": 1.0,
            "lag1": trend.lag1
            if all(right - left == 1 for left, right in pairwise(years))
            else None,
        }
    )
