"""Regression coverage for the review findings and the frozen inference contract."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import beta, theilslopes

from app.catalogue import get_entry
from app.models import AnalyzeTrendInput, ComparePlacesInput, PlaceInput
from app.tools.context import ToolContext
from app.tools.inference import TABLE_SHA256, analyse_values, calibrated_p, load_table
from app.tools.trends import analyze_trend, compare_places
from app.verdict import build_verdict
from tests.fake_source import FakeSource, line, monthly_from_yearly


def test_descriptive_sen_estimator_matches_independent_scipy_reference() -> None:
    years = list(range(1981, 2026))
    values = (np.random.default_rng(42).normal(size=45) + np.arange(45) * 0.05).tolist()
    result = analyse_values(years, values, get_entry("air_temp"), "annual")
    assert result.sen_slope == pytest.approx(theilslopes(np.round(values, 9), years).slope * 10)
    assert result.mk_p is not None
    assert result.sen_ci95 is None and result.ols_p is None
    assert result.method_id == "mk_mc_envelope_v1"


@pytest.mark.parametrize("n", [10, 12, 19, 46])
def test_records_outside_the_validated_length_have_no_inference(n: int) -> None:
    result = analyse_values(
        list(range(1980, 1980 + n)), list(map(float, range(n))), get_entry("air_temp"), "annual"
    )
    assert result.mk_p is None and result.inference_status == "unavailable"
    assert result.sen_slope == 10
    assert result.inference_reason


def test_a_missing_year_is_not_compressed_into_a_lag_one_neighbor() -> None:
    years = [year for year in range(2000, 2021) if year != 2010]
    result = analyse_values(years, list(map(float, years)), get_entry("air_temp"), "annual")
    assert result.mk_p is None
    assert "Missing years" in result.inference_reason
    assert result.lag1 is None
    assert result.sen_slope == 10


@pytest.mark.parametrize(
    "variable,season",
    [
        ("sunlight", "annual"),
        ("cloud_cover", "annual"),
        ("precipitation", "annual"),
        ("air_temp", "DJF"),
    ],
)
def test_unvalidated_quantities_and_seasons_do_not_borrow_temperature_inference(
    variable: str, season: str
) -> None:
    result = analyse_values(
        list(range(1984, 2026)), list(map(float, range(42))), get_entry(variable), season
    )
    assert result.mk_p is None
    assert result.sen_ci95 is None
    if variable in ("sunlight", "cloud_cover"):
        assert "source transition" in result.inference_reason


def test_constants_have_zero_rate_without_claiming_absence_of_all_change() -> None:
    result = analyse_values(list(range(1981, 2026)), [2.0] * 45, get_entry("air_temp"), "annual")
    assert result.sen_slope == 0 and result.mk_p == 1


def test_significant_tied_rank_pattern_can_have_a_zero_median_pairwise_rate() -> None:
    values = [0.0] * 32 + list(map(float, range(1, 14)))
    entry = get_entry("air_temp")
    result = analyse_values(list(range(1981, 2026)), values, entry, "annual")
    assert result.sen_slope == 0
    assert result.mk_p < 0.05
    verdict = build_verdict(entry, "Synthetic reference case", 45, result)
    assert verdict.kind == "significant"
    assert verdict.direction is None
    assert "does not establish that no change occurred" in verdict.sentence


def test_corrupt_or_missing_tables_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    assert load_table(missing) is None
    missing.write_text("{}", encoding="utf-8")
    load_table.cache_clear()
    assert load_table(missing) is None
    assert load_table() is not None


def test_frozen_table_and_all_confirmation_settings_match_the_gate() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (
        hashlib.sha256((root / "backend/data/inference-v1.json").read_bytes()).hexdigest()
        == TABLE_SHA256
    )
    report = json.loads((root / "research/inference-results.json").read_text())
    assert report["table_sha256"] == TABLE_SHA256
    assert len(report["settings"]) == 18
    complete = json.loads((root / "research/inference-confirmation-all-lengths.json").read_text())
    assert len(complete["settings"]) == 156
    assert complete["table_sha256"] == TABLE_SHA256
    assert all(row["upper95"] <= 0.07 for row in complete["settings"] + complete["ties_stress"])
    assert complete["constant_p"] == 1
    assert all(row["replicates"] == 4000 and row["upper95"] <= 0.07 for row in report["settings"])


def test_serially_correlated_zero_trend_noise_passes_the_release_guardrail() -> None:
    rng = np.random.default_rng(202611145)
    years = list(range(1981, 2026))
    rejected = 0
    for _ in range(4000):
        noise = rng.normal(size=45)
        x = np.empty(45)
        x[0] = noise[0] / np.sqrt(0.75)
        for t in range(1, 45):
            x[t] = 0.5 * x[t - 1] + noise[t]
        rejected += calibrated_p(years, x) < 0.05
    assert beta.ppf(0.95, rejected + 1, 4000 - rejected) <= 0.07


@pytest.mark.anyio
async def test_comparison_uses_identical_complete_years_and_exposes_them() -> None:
    first = monthly_from_yearly(line(0.1, 2000, 2020))
    second = {**first, (2000, 1): None}
    source = FakeSource(by_point={(0.0, 0.0): first, (1.0, 0.0): second})
    inp = ComparePlacesInput.model_validate(
        {
            "variable": "air_temp",
            "places": [{"lat": 0, "lon": 0, "name": "A"}, {"lat": 1, "lon": 0, "name": "B"}],
            "from": 2000,
            "to": 2020,
        }
    )
    result = await compare_places(inp, ToolContext(source, 2025))
    assert result.common_years == list(range(2001, 2021))
    assert [place.trend.n for place in result.results] == [20, 20]
    assert all(place.analysis_years == result.common_years for place in result.results)
    assert all(place.trend.mk_p is None for place in result.results)
    assert "not a statistical test of differences" in result.summary


@pytest.mark.anyio
async def test_original_coordinate_selects_the_cell_before_link_serialization() -> None:
    source = FakeSource(monthly_from_yearly(line(0.05)))
    result = await analyze_trend(
        AnalyzeTrendInput(variable="air_temp", place=PlaceInput(lat=0.249, lon=0)),
        ToolContext(source, 2025),
    )
    assert result.results[0].place.cell.lat == 0
    assert "p=0.249,0" in result.app_url


@pytest.mark.anyio
@pytest.mark.parametrize("missing", [2000, 2020])
async def test_missing_endpoint_year_requires_explicit_period_confirmation(missing: int) -> None:
    yearly = line(0.1, 2000, 2020)
    yearly[missing] = None
    source = FakeSource(monthly_from_yearly(yearly))
    ctx = ToolContext(source, 2025)
    inp = AnalyzeTrendInput.model_validate(
        {"variable": "air_temp", "place": {"lat": 0, "lon": 0}, "from": 2000, "to": 2020}
    )
    result = (await analyze_trend(inp, ctx)).results[0]
    assert result.trend.n == 20
    assert result.trend.mk_p is None
    assert "Missing years" in result.trend.inference_reason
    confirmed = inp.model_copy(
        update={"from_": 2001, "to": 2020} if missing == 2000 else {"from_": 2000, "to": 2019}
    )
    assert (await analyze_trend(confirmed, ctx)).results[0].trend.mk_p is not None


@pytest.mark.anyio
async def test_disjoint_coverage_is_not_reported_as_absent_source_data() -> None:
    source = FakeSource(
        by_point={
            (0.0, 0.0): monthly_from_yearly(line(0.1, 2000, 2009)),
            (1.0, 0.0): monthly_from_yearly(line(0.1, 2010, 2020)),
        }
    )
    inp = ComparePlacesInput.model_validate(
        {
            "variable": "air_temp",
            "from": 2000,
            "to": 2020,
            "places": [{"lat": 0, "lon": 0}, {"lat": 1, "lon": 0}],
        }
    )
    result = await compare_places(inp, ToolContext(source, 2025))
    assert result.common_years == []
    assert all(place.verdict.kind == "inference_unavailable" for place in result.results)
    assert all("no year in the period" not in step for step in result.steps)
