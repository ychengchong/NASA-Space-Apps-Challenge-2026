"""The whole world (spec 7): a frozen world-mean sample, read without NASA, descriptive only."""

import math
from datetime import date
from pathlib import Path

import pytest

from app.cache import Cache
from app.catalogue import load_catalogue
from app.errors import SourceUnavailableError, UnsupportedRequestError
from app.models import PlaceInput, WorldTrendInput
from app.sources.base import PointSeries
from app.tools import trends
from app.tools.places import resolve_place
from app.tools.trends import WorldMeanDocument, world_trend
from scripts.build_world_mean import (
    SAMPLE_LATITUDES,
    SAMPLE_LONGITUDES,
    SampleSeries,
    grids,
    sample_points,
    world_document,
    world_means,
)
from tests.app_client import make_services
from tests.fake_source import FakeSource
from tests.test_rest import client_for
from tests.test_tools import context

WORLD_FILE = Path(__file__).parents[1] / "data" / "world-mean.json"


def monthly_line(slope_per_year: float, first_year: int = 1981) -> dict[str, float | None]:
    return {
        f"{year:04d}-{month:02d}": 14.0 + slope_per_year * (year - first_year)
        for year in range(first_year, 2026)
        for month in range(1, 13)
    }


def fake_document() -> WorldMeanDocument:
    return {
        "schema": "world_mean_v1",
        "built": "2026-11-15",
        "end_year": 2025,
        "sample": {
            "step_degrees": 20,
            "latitudes": list(SAMPLE_LATITUDES),
            "longitudes": list(SAMPLE_LONGITUDES),
            "points": 162,
        },
        "api_versions": ["v2.10.0"],
        "accessed": ["2026-11-15"],
        "variables": {"air_temp": monthly_line(0.02), "haze": monthly_line(0.001, 2001)},
    }


@pytest.fixture
def frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trends, "load_world_mean", fake_document)


@pytest.mark.anyio
@pytest.mark.usefixtures("frozen")
async def test_the_world_case_reads_the_frozen_sample_and_calls_no_source() -> None:
    source = FakeSource()

    world = await world_trend(WorldTrendInput(variable="air_temp"), context(source))

    assert source.calls == []
    assert world.result.trend is not None
    assert world.result.trend.sen_slope == pytest.approx(0.2)
    assert world.points == 162


@pytest.mark.anyio
@pytest.mark.usefixtures("frozen")
async def test_the_world_verdict_names_the_sample_and_is_never_assessed() -> None:
    world = await world_trend(WorldTrendInput(variable="air_temp"), context(FakeSource()))

    verdict = world.result.verdict
    assert verdict.kind == "inference_unavailable"
    assert world.result.trend is not None and world.result.trend.mk_p is None
    assert verdict.sentence == (
        "The estimated change in air temperature averaged over a sample of 162 grid points "
        "across the whole world is +0.20 °C per decade over 1981-2025. This is an estimate from "
        "a sample, and significance has not been assessed."
    )
    assert "grid cell containing" not in verdict.sentence


@pytest.mark.anyio
@pytest.mark.usefixtures("frozen")
async def test_the_world_page_says_it_is_a_sample_and_how_large() -> None:
    world = await world_trend(WorldTrendInput(variable="air_temp"), context(FakeSource()))

    assert "sample of 162 grid points" in world.sample_note
    assert "rainfall or wind" in world.sample_note
    assert any("fixed sample of 162 grid points" in step for step in world.steps)
    assert any("No NASA service is called" in step for step in world.steps)
    assert world.sources[0].provenance_status == "prepared_sample_mean"
    assert "162-point sample" in world.sources[0].product


@pytest.mark.anyio
@pytest.mark.usefixtures("frozen")
async def test_the_world_case_has_record_years_and_a_link() -> None:
    world = await world_trend(WorldTrendInput(variable="haze"), context(FakeSource()))

    assert world.result.records is not None
    assert world.requested.from_ == 2001
    assert world.app_url.endswith("/world?v=haze&from=2001&to=2025&s=annual")


@pytest.mark.anyio
@pytest.mark.usefixtures("frozen")
async def test_a_land_only_variable_has_no_world_mean() -> None:
    with pytest.raises(UnsupportedRequestError):
        await world_trend(WorldTrendInput(variable="snow_depth"), context(FakeSource()))


@pytest.mark.anyio
async def test_a_missing_world_file_is_reported_not_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(trends, "load_world_mean", lambda: None)

    with pytest.raises(SourceUnavailableError):
        await world_trend(WorldTrendInput(variable="air_temp"), context(FakeSource()))


@pytest.mark.usefixtures("frozen")
def test_world_endpoint_answers_and_refuses_snow(tmp_path: Path) -> None:
    client = client_for(make_services(Cache(tmp_path / "cache.sqlite"), FakeSource()), tmp_path)

    answer = client.get("/api/world?v=air_temp&from=1981&to=2025&s=annual")
    snow = client.get("/api/world?v=snow_depth")

    assert answer.status_code == 200
    assert answer.json()["result"]["place"]["name"] == "the whole world"
    assert snow.status_code == 422
    assert snow.json()["error"]["code"] == "unsupported_request"


# The build script


def test_the_sample_is_162_points_every_20_degrees() -> None:
    points = sample_points()

    assert len(points) == 162
    assert points[0] == (-80.0, -180.0)
    assert points[-1] == (80.0, 160.0)


def test_world_means_weight_by_latitude_and_keep_the_footprint_fixed() -> None:
    points = [(0.0, 0.0), (60.0, 0.0)]
    sample: SampleSeries = {}
    for lat, lon in points:
        for grid in grids():
            entry = next(item for item in load_catalogue() if item.grid == grid)
            cell = resolve_place(PlaceInput(lat=lat, lon=lon), entry).cell
            value = 10.0 if lat == 0.0 else 20.0
            missing = lat == 60.0
            sample[(grid, cell.lat, cell.lon)] = {
                item.code: PointSeries(
                    item.code,
                    cell.lat,
                    cell.lon,
                    {(2000, 1): value, (2000, 2): None if missing else value},
                    "v2.10.0",
                    "2026-11-15",
                )
                for item in load_catalogue()
                if item.grid == grid
            }

    means = world_means(sample, points)

    weight_equator, weight_sixty = 1.0, math.cos(math.radians(60.0))
    expected = (10.0 * weight_equator + 20.0 * weight_sixty) / (weight_equator + weight_sixty)
    assert means["air_temp"]["2000-01"] == pytest.approx(expected)
    assert means["air_temp"]["2000-02"] is None
    assert set(means) == {entry.id for entry in load_catalogue() if entry.world_mean}


def test_the_world_document_records_its_sample_and_provenance() -> None:
    points = [(0.0, 0.0)]
    sample: SampleSeries = {}
    for grid in grids():
        entry = next(item for item in load_catalogue() if item.grid == grid)
        cell = resolve_place(PlaceInput(lat=0.0, lon=0.0), entry).cell
        sample[(grid, cell.lat, cell.lon)] = {
            item.code: PointSeries(
                item.code, cell.lat, cell.lon, {(2000, 1): 1.0}, "v2.10.0", "2026-11-15"
            )
            for item in load_catalogue()
            if item.grid == grid
        }

    document = world_document(sample, points, 2025, date(2026, 11, 15))

    assert document["schema"] == "world_mean_v1"
    assert document["sample"]["points"] == 1
    assert document["api_versions"] == ["v2.10.0"]
    assert document["built"] == "2026-11-15"


def test_no_land_only_or_sea_only_variable_is_in_the_world_mean() -> None:
    covered = {entry.id for entry in load_catalogue() if entry.world_mean}

    assert not covered & {
        "snow_depth",
        "snowfall",
        "snow_cover",
        "sea_ice",
        "surface_soil_wetness",
        "root_zone_soil_wetness",
    }


def test_the_shipped_world_file_covers_exactly_the_marked_variables() -> None:
    document = trends.load_world_mean(WORLD_FILE)

    assert document is not None
    assert document["sample"]["points"] == len(sample_points())
    assert set(document["variables"]) == {
        entry.id for entry in load_catalogue() if entry.world_mean
    }
