"""What every tool receives besides its input: the data source, the period limit, the link base."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.snapshots import SnapshotStore
from app.sources.base import SeriesSource

# Spec 6: on 13 November 2026 POWER had monthly values up to September 2026, so December of a
# year is assumed available once this many days have passed since the end of that December.
POWER_MONTHLY_LAG_DAYS = 75


def last_complete_year(today: date) -> int:
    """The latest year whose twelve months the source is expected to have published by `today`."""
    return (today - timedelta(days=POWER_MONTHLY_LAG_DAYS)).year - 1


@dataclass(frozen=True)
class ToolContext:
    source: SeriesSource
    last_complete_year: int
    public_base_url: str | None = None
    snapshots: SnapshotStore = field(default_factory=SnapshotStore)
