"""Pinned evidence is immutable and never falls back to changing live data."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.adapters.case_query import parse_case_query, parse_query_string
from app.cache import Cache
from app.errors import BadRequestError, SourceUnavailableError
from app.models import AnalyzeTrendInput, GetSeriesInput, PlaceInput
from app.snapshots import SnapshotStore
from app.tools.context import ToolContext
from app.tools.series import get_series
from app.tools.trends import analyze_trend
from tests.fake_source import FakeSource, line, monthly_from_yearly


def test_snapshot_checksum_and_invalid_paths_are_checked(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    identity = store.put(b'{"immutable":true}')
    assert store.get(identity) == b'{"immutable":true}'
    assert store.put(b'{"immutable":true}') == identity
    with pytest.raises(BadRequestError):
        store.get("../credentials")
    (tmp_path / f"{identity}.json").write_bytes(b"changed")
    with pytest.raises(SourceUnavailableError, match="integrity"):
        store.get(identity)


@pytest.mark.anyio
async def test_pinned_case_and_csv_series_survive_refresh_and_restart(tmp_path: Path) -> None:
    source = FakeSource(monthly_from_yearly(line(0.05)))
    inp = AnalyzeTrendInput(variable="air_temp", place=PlaceInput(lat=0, lon=0))
    ctx = ToolContext(source, 2025, snapshots=SnapshotStore(tmp_path))
    original = await analyze_trend(inp, ctx)
    pinned = parse_case_query(parse_query_string(original.app_url.split("?")[1]))
    changed = FakeSource(monthly_from_yearly(line(-0.05)))
    reopened = ToolContext(changed, 2025, snapshots=SnapshotStore(tmp_path))
    result = await analyze_trend(pinned, reopened)
    assert result.id == original.id
    assert result.model_dump() == original.model_dump()
    assert changed.calls == []
    fresh = await analyze_trend(inp, reopened)
    assert fresh.id != original.id
    series = await get_series(
        GetSeriesInput.model_validate(
            {**pinned.model_dump(exclude={"scan"}), "resolution": "yearly"}
        ),
        reopened,
    )
    assert series.values[0].value == original.results[0].series[0].value
    assert series.values[-1].value == original.results[0].series[-1].value


@pytest.mark.anyio
async def test_missing_pin_unknown_version_and_wrong_cell_never_refresh_live() -> None:
    source = FakeSource(monthly_from_yearly(line(0.05)))
    ctx = ToolContext(source, 2025)
    inp = AnalyzeTrendInput(
        variable="air_temp",
        place=PlaceInput(lat=0, lon=0),
        snapshot_ids=["a" * 64],
        analysis_version="td-2026-11-v1",
    )
    with pytest.raises(SourceUnavailableError):
        await analyze_trend(inp, ctx)
    with pytest.raises(BadRequestError, match="version"):
        await analyze_trend(inp.model_copy(update={"analysis_version": "unknown"}), ctx)
    assert source.calls == []
    original = await analyze_trend(inp.model_copy(update={"snapshot_ids": []}), ctx)
    with pytest.raises(BadRequestError, match="grid cell"):
        await analyze_trend(
            inp.model_copy(
                update={
                    "snapshot_ids": [original.results[0].snapshot_id],
                    "place": PlaceInput(lat=5, lon=0),
                }
            ),
            ctx,
        )
    assert len(source.calls) == 1


def test_atomic_budget_reservations_are_durable_across_connections(tmp_path: Path) -> None:
    path = tmp_path / "operations.sqlite"
    first, second = Cache(path), Cache(path)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            approved = list(
                pool.map(
                    lambda i: (first if i % 2 else second).reserve_budget("2026-11-14", 100, 1000),
                    range(40),
                )
            )
        assert sum(approved) == 10
        assert first.get_counter("budget_microusd", "2026-11-14") == 1000
        assert not second.reserve_budget("2026-11-14", 1, 1000)
        assert first.reserve_budget("2026-11-15", 100, 1000)
        assert first.acquire_lease("generation", "one", 10, 30)
        assert not second.acquire_lease("generation", "two", 20, 30)
        second.release_lease("generation", "two")
        assert not second.acquire_lease("generation", "two", 25, 30)
        assert second.acquire_lease("generation", "two", 41, 30)
    finally:
        first.close()
        second.close()


def test_concurrent_snapshot_writers_only_publish_complete_bytes(tmp_path: Path) -> None:
    content = b'{"record": "' + b"x" * 250_000 + b'"}'
    stores = [SnapshotStore(tmp_path) for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        identities = list(pool.map(lambda store: store.put(content), stores))
    assert len(set(identities)) == 1
    assert all(store.get(identities[0]) == content for store in stores)


@pytest.mark.anyio
async def test_new_source_download_retains_exact_raw_bytes_and_query(tmp_path: Path) -> None:
    import httpx

    from app.sources.power import PowerClient

    raw = (Path(__file__).parent / "fixtures/power_point_full.json").read_bytes()
    cache = Cache(tmp_path / "cache.sqlite")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw))
    ) as http:
        source = PowerClient(cache, http=http)
        series = (await source.point_series(60.0, 25.0, ["T2M"], 2025))["T2M"]
        assert series.raw_sha256 is not None
        assert cache.snapshots.get(series.raw_sha256) == raw
        assert series.query_url.startswith(
            "https://power.larc.nasa.gov/api/temporal/monthly/point?"
        )
        identity = cache.snapshots.freeze(series)
        assert cache.snapshots.series(identity) == series
        cached = (await source.point_series(60.0, 25.0, ["T2M"], 2025))["T2M"]
        assert cached.raw_sha256 == series.raw_sha256
    cache.close()
