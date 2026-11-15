import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.cache import Cache
from app.sources.base import PointSeries

SOURCE = "power"


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "cache.sqlite"


@pytest.fixture
def cache(cache_path: Path) -> Iterator[Cache]:
    opened = Cache(cache_path)
    yield opened
    opened.close()


def make_series(
    code: str = "T2M", lat: float = 60.0, lon: float = 25.0, first_value: float | None = 1.5
) -> PointSeries:
    return PointSeries(
        code=code,
        lat=lat,
        lon=lon,
        monthly={(1981, 1): first_value, (1981, 2): None, (2025, 12): -3.25},
        version="v2.10.0",
        accessed="2026-11-13",
    )


def test_creates_file_and_tables_when_missing(tmp_path: Path) -> None:
    path = tmp_path / "new" / "folder" / "cache.sqlite"
    cache = Cache(path)
    assert path.exists()
    assert cache.read_point_series(SOURCE, 60.0, 25.0, ["T2M"], 2025) == {}
    assert cache.get_counter("ai_turns", "2026-11-13") == 0
    cache.close()


def test_written_series_reads_back_with_missing_months_as_none(cache: Cache) -> None:
    series = make_series()
    cache.write_point_series(SOURCE, [series], end_year=2025)
    assert cache.read_point_series(SOURCE, 60.0, 25.0, ["T2M"], 2025) == {"T2M": series}


def test_read_returns_only_the_requested_codes(cache: Cache) -> None:
    cache.write_point_series(SOURCE, [make_series("T2M"), make_series("TS")], end_year=2025)
    assert set(cache.read_point_series(SOURCE, 60.0, 25.0, ["TS", "RH2M"], 2025)) == {"TS"}


def test_read_leaves_out_series_fetched_only_to_an_earlier_year(cache: Cache) -> None:
    cache.write_point_series(SOURCE, [make_series()], end_year=2024)
    assert cache.read_point_series(SOURCE, 60.0, 25.0, ["T2M"], 2025) == {}
    assert set(cache.read_point_series(SOURCE, 60.0, 25.0, ["T2M"], 2023)) == {"T2M"}


def test_rows_are_keyed_by_source_and_grid_point(cache: Cache) -> None:
    cache.write_point_series(SOURCE, [make_series(lat=60.0, lon=25.0)], end_year=2025)
    assert cache.read_point_series(SOURCE, 60.0, 25.625, ["T2M"], 2025) == {}
    assert cache.read_point_series(SOURCE, 60.5, 25.0, ["T2M"], 2025) == {}
    assert cache.read_point_series("other", 60.0, 25.0, ["T2M"], 2025) == {}


def test_coordinates_that_differ_only_by_rounding_share_a_row(cache: Cache) -> None:
    cache.write_point_series(SOURCE, [make_series(lon=0.1 + 0.2)], end_year=2025)
    assert set(cache.read_point_series(SOURCE, 60.0, 0.3, ["T2M"], 2025)) == {"T2M"}


def test_newer_fetch_replaces_a_row(cache: Cache) -> None:
    cache.write_point_series(SOURCE, [make_series(first_value=1.0)], end_year=2024)
    cache.write_point_series(SOURCE, [make_series(first_value=2.0)], end_year=2025)
    stored = cache.read_point_series(SOURCE, 60.0, 25.0, ["T2M"], 2025)["T2M"]
    assert stored.monthly[(1981, 1)] == 2.0


def test_fetch_ending_earlier_never_replaces_a_row(cache: Cache) -> None:
    cache.write_point_series(SOURCE, [make_series(first_value=2.0)], end_year=2025)
    cache.write_point_series(SOURCE, [make_series(first_value=1.0)], end_year=2024)
    stored = cache.read_point_series(SOURCE, 60.0, 25.0, ["T2M"], 2025)["T2M"]
    assert stored.monthly[(1981, 1)] == 2.0


def test_series_persist_across_instances(cache_path: Path) -> None:
    first = Cache(cache_path)
    first.write_point_series(SOURCE, [make_series()], end_year=2025)
    first.close()
    second = Cache(cache_path)
    assert second.read_point_series(SOURCE, 60.0, 25.0, ["T2M"], 2025) == {"T2M": make_series()}
    second.close()


def test_increment_counter_returns_the_new_count(cache: Cache) -> None:
    assert [cache.increment_counter("ai_turns", "2026-11-14") for _ in range(3)] == [1, 2, 3]
    assert cache.get_counter("ai_turns", "2026-11-14") == 3


def test_counters_are_separate_per_key_and_day(cache: Cache) -> None:
    cache.increment_counter("ai_turns", "2026-11-14")
    assert cache.get_counter("ai_turns", "2026-11-15") == 0
    assert cache.get_counter("other", "2026-11-14") == 0


def test_counters_persist_across_instances(cache_path: Path) -> None:
    first = Cache(cache_path)
    first.increment_counter("ai_turns", "2026-11-14")
    first.increment_counter("ai_turns", "2026-11-14")
    first.close()
    second = Cache(cache_path)
    assert second.increment_counter("ai_turns", "2026-11-14") == 3
    second.close()


def test_counter_counts_every_increment_from_many_threads(cache: Cache) -> None:
    threads_count, increments_per_thread = 8, 50

    def increment_many() -> None:
        for _ in range(increments_per_thread):
            cache.increment_counter("ai_turns", "2026-11-14")

    threads = [threading.Thread(target=increment_many) for _ in range(threads_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert cache.get_counter("ai_turns", "2026-11-14") == threads_count * increments_per_thread


def test_rows_of_a_newer_seed_are_added_and_existing_rows_kept(tmp_path: Path) -> None:
    seed = Cache(tmp_path / "seed.sqlite")
    seed.write_point_series(
        "power",
        [
            PointSeries("T2M", 60.0, 25.0, {(2000, 1): 1.0}, "v-seed", "2026-11-13"),
            PointSeries("SNODP", 60.0, 25.0, {(2000, 1): 5.0}, "v-seed", "2026-11-14"),
        ],
        2025,
    )
    seed.close()
    state = Cache(tmp_path / "state.sqlite")
    state.write_point_series(
        "power", [PointSeries("T2M", 60.0, 25.0, {(2000, 1): 2.0}, "v-state", "2026-11-01")], 2025
    )

    added = state.add_missing_rows(tmp_path / "seed.sqlite")
    rows = state.read_point_series("power", 60.0, 25.0, ["T2M", "SNODP"], 2025)
    again = state.add_missing_rows(tmp_path / "seed.sqlite")
    state.close()

    assert added == 1
    assert again == 0
    assert rows["T2M"].version == "v-state"
    assert rows["SNODP"].monthly == {(2000, 1): 5.0}


# The investigation lookup for explanations (spec 8, "Planned explanations")

INVESTIGATION_ID = "e" * 64
PINNED_QUERY = "v=air_temp&p=60.17,24.94&from=1981&to=2025&s=annual&snap=abc&av=td-2026-11-v1"


def test_recorded_investigation_is_found_by_its_id(cache: Cache) -> None:
    cache.record_investigation(INVESTIGATION_ID, PINNED_QUERY, "td-2026-11-v1", 1000.0)

    record = cache.find_investigation(INVESTIGATION_ID)

    assert record is not None
    assert record.case_query == PINNED_QUERY
    assert record.analysis_version == "td-2026-11-v1"
    assert record.created == 1000.0


def test_unrecorded_investigation_is_not_found(cache: Cache) -> None:
    assert cache.find_investigation(INVESTIGATION_ID) is None


def test_recording_an_id_again_keeps_the_first_record(cache: Cache) -> None:
    cache.record_investigation(INVESTIGATION_ID, PINNED_QUERY, "td-2026-11-v1", 1000.0)
    cache.record_investigation(INVESTIGATION_ID, "v=other", "td-2026-11-v1", 2000.0)

    record = cache.find_investigation(INVESTIGATION_ID)

    assert record is not None
    assert (record.case_query, record.created) == (PINNED_QUERY, 1000.0)


def test_investigation_records_older_than_the_retention_are_pruned(cache: Cache) -> None:
    other_id = "f" * 64
    cache.record_investigation(INVESTIGATION_ID, PINNED_QUERY, "td-2026-11-v1", 1000.0)

    cache.record_investigation(
        other_id, "v=rain", "td-2026-11-v1", 1000.0 + 86_401.0, retention_seconds=86_400.0
    )

    assert cache.find_investigation(INVESTIGATION_ID) is None
    assert cache.find_investigation(other_id) is not None


def test_investigation_record_within_the_retention_is_kept(cache: Cache) -> None:
    cache.record_investigation(INVESTIGATION_ID, PINNED_QUERY, "td-2026-11-v1", 1000.0)

    cache.record_investigation(
        "f" * 64, "v=rain", "td-2026-11-v1", 1000.0 + 86_399.0, retention_seconds=86_400.0
    )

    assert cache.find_investigation(INVESTIGATION_ID) is not None


def test_expired_investigation_is_recorded_afresh(cache: Cache) -> None:
    cache.record_investigation(INVESTIGATION_ID, PINNED_QUERY, "td-2026-11-v1", 1000.0)

    cache.record_investigation(
        INVESTIGATION_ID, PINNED_QUERY, "td-2026-11-v1", 100_000.0, retention_seconds=86_400.0
    )

    record = cache.find_investigation(INVESTIGATION_ID)
    assert record is not None and record.created == 100_000.0


def test_only_the_newest_investigation_records_are_kept(cache: Cache) -> None:
    ids = [character * 64 for character in "abc"]
    for created, investigation_id in enumerate(ids):
        cache.record_investigation(
            investigation_id, PINNED_QUERY, "td-2026-11-v1", float(created), max_rows=2
        )

    assert cache.find_investigation(ids[0]) is None
    assert cache.find_investigation(ids[1]) is not None
    assert cache.find_investigation(ids[2]) is not None


def test_investigation_record_survives_reopening_the_file(cache_path: Path) -> None:
    first = Cache(cache_path)
    first.record_investigation(INVESTIGATION_ID, PINNED_QUERY, "td-2026-11-v1", 1000.0)
    first.close()

    reopened = Cache(cache_path)
    record = reopened.find_investigation(INVESTIGATION_ID)
    reopened.close()

    assert record is not None and record.case_query == PINNED_QUERY
