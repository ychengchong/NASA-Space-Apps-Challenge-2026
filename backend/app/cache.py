"""SQLite store for NASA values and the daily usage counters.

Spec 6, "Caching": one row per source, grid point and code. Completed years do not change, so
rows never expire. Spec 8, "Limits": the daily AI counters live in the same file, so a restart
does not reset them.
"""

import json
import sqlite3
import threading
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from app.snapshots import SnapshotStore
from app.sources.base import MonthKey, MonthlyValues, PointSeries

# A grid coordinate read from a response and the same coordinate computed by grid snapping can
# differ in the last bits; rounding both to this many decimals makes them name one row.
COORDINATE_DECIMALS = 6

_SCHEMA = """
CREATE TABLE IF NOT EXISTS point_series (
    source   TEXT    NOT NULL,
    lat      REAL    NOT NULL,
    lon      REAL    NOT NULL,
    code     TEXT    NOT NULL,
    monthly  TEXT    NOT NULL,  -- JSON object {"YYYY-MM": value or null}
    version  TEXT    NOT NULL,
    accessed TEXT    NOT NULL,  -- YYYY-MM-DD
    end_year INTEGER NOT NULL,  -- the last year that was requested from the source
    PRIMARY KEY (source, lat, lon, code)
);
CREATE TABLE IF NOT EXISTS counters (
    key   TEXT    NOT NULL,
    day   TEXT    NOT NULL,
    value INTEGER NOT NULL,
    PRIMARY KEY (key, day)
);
CREATE TABLE IF NOT EXISTS leases (
    key TEXT PRIMARY KEY, token TEXT NOT NULL, expires REAL NOT NULL
);
"""

# A newer fetch replaces a row; a fetch that ended in an earlier year never does.
_UPSERT_SERIES = """
INSERT INTO point_series (source, lat, lon, code, monthly, version, accessed, end_year)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (source, lat, lon, code) DO UPDATE SET
    monthly = excluded.monthly,
    version = excluded.version,
    accessed = excluded.accessed,
    end_year = excluded.end_year
WHERE excluded.end_year >= point_series.end_year
"""

_INCREMENT_COUNTER = """
INSERT INTO counters (key, day, value) VALUES (?, ?, 1)
ON CONFLICT (key, day) DO UPDATE SET value = value + 1
RETURNING value
"""


class Cache:
    """The SQLite file. Safe to share between async code and threads: one connection, one lock."""

    def __init__(self, path: Path, snapshots: SnapshotStore | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self.snapshots = snapshots or SnapshotStore(path.parent / "snapshots")
        with self._lock, self._connection:
            self._connection.executescript(_SCHEMA)
            columns = {
                row[1] for row in self._connection.execute("PRAGMA table_info(point_series)")
            }
            for column in ("raw_sha256", "query_url", "product"):
                if column not in columns:
                    self._connection.execute(f"ALTER TABLE point_series ADD COLUMN {column} TEXT")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def read_point_series(
        self, source: str, lat: float, lon: float, codes: Sequence[str], min_end_year: int
    ) -> dict[str, PointSeries]:
        """The cached series of `codes` at one grid point, keyed by code.

        A code is left out when it is not cached, or when it was fetched only up to a year
        before `min_end_year`. Missing months come back as None. Each series holds every month
        stored, which may run past `min_end_year`.
        """
        if not codes:
            return {}
        placeholders = ", ".join("?" for _ in codes)
        query = (
            "SELECT code, monthly, version, accessed, raw_sha256, query_url, product "
            "FROM point_series"
            " WHERE source = ? AND lat = ? AND lon = ? AND end_year >= ?"
            f" AND code IN ({placeholders})"
        )
        with self._lock:
            rows = self._connection.execute(
                query, (source, _coordinate(lat), _coordinate(lon), min_end_year, *codes)
            ).fetchall()
        return {
            code: PointSeries(
                code=code,
                lat=lat,
                lon=lon,
                monthly=_decode_monthly(monthly),
                version=version,
                accessed=accessed,
                raw_sha256=raw_sha256,
                query_url=query_url,
                product=product,
            )
            for code, monthly, version, accessed, raw_sha256, query_url, product in rows
        }

    def write_point_series(self, source: str, series: Iterable[PointSeries], end_year: int) -> None:
        """Store each series under its own grid point and code, as fetched up to `end_year`.

        A row already fetched up to a later year is kept.
        """
        series = list(series)
        rows = [
            (
                source,
                _coordinate(item.lat),
                _coordinate(item.lon),
                item.code,
                _encode_monthly(item.monthly),
                item.version,
                item.accessed,
                end_year,
            )
            for item in series
        ]
        with self._lock, self._connection:
            self._connection.executemany(_UPSERT_SERIES, rows)
            for item in series:
                self._connection.execute(
                    "UPDATE point_series SET raw_sha256=?, query_url=?, product=? "
                    "WHERE source=? AND lat=? AND lon=? AND code=? AND end_year=?",
                    (
                        item.raw_sha256,
                        item.query_url,
                        item.product,
                        source,
                        _coordinate(item.lat),
                        _coordinate(item.lon),
                        item.code,
                        end_year,
                    ),
                )

    def increment_counter(self, key: str, day: str) -> int:
        """Add one to the counter `key` for `day` ("YYYY-MM-DD") and return the new count."""
        with self._lock, self._connection:
            (value,) = self._connection.execute(_INCREMENT_COUNTER, (key, day)).fetchone()
        return int(value)

    def get_counter(self, key: str, day: str) -> int:
        """The count of `key` for `day` ("YYYY-MM-DD"); 0 when it was never incremented."""
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM counters WHERE key = ? AND day = ?", (key, day)
            ).fetchone()
        return 0 if row is None else int(row[0])

    def reserve_budget(self, day: str, amount: int, limit: int) -> bool:
        """Atomically reserve integer microdollars; attempts, failures and cancellations consume it.

        Never refund an uncertain provider outcome. SQLite serializes this statement
        across processes as well as threads, including the initial insert.
        """
        if amount <= 0 or amount > limit:
            return False
        with self._lock, self._connection:
            row = self._connection.execute(
                "INSERT INTO counters(key,day,value) VALUES('budget_microusd',?,?) "
                "ON CONFLICT(key,day) DO UPDATE SET value=value+excluded.value "
                "WHERE value+excluded.value<=? RETURNING value",
                (day, amount, limit),
            ).fetchone()
        return row is not None

    def acquire_lease(self, key: str, token: str, now: float, seconds: float) -> bool:
        """Bound concurrent generations across workers sharing the operational database."""
        with self._lock, self._connection:
            row = self._connection.execute(
                "INSERT INTO leases(key,token,expires) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET token=excluded.token,expires=excluded.expires "
                "WHERE expires<=? RETURNING token",
                (key, token, now + seconds, now),
            ).fetchone()
        return row is not None

    def release_lease(self, key: str, token: str) -> None:
        """Release only this request's lease; never release a newer owner's generation."""
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM leases WHERE key=? AND token=?", (key, token))


def _coordinate(value: float) -> float:
    return round(value, COORDINATE_DECIMALS)


def _encode_monthly(monthly: MonthlyValues) -> str:
    return json.dumps(
        {f"{year:04d}-{month:02d}": value for (year, month), value in sorted(monthly.items())}
    )


def _decode_monthly(text: str) -> dict[MonthKey, float | None]:
    stored: Mapping[str, float | None] = json.loads(text)
    monthly: dict[MonthKey, float | None] = {}
    for key, value in stored.items():
        year, month = key.split("-")
        monthly[(int(year), int(month))] = value
    return monthly
