"""The long-lived objects the adapters share: settings, the cache and the data source."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from app.cache import Cache
from app.config import DATA_DIR, Settings
from app.ratelimit import RateLimiter
from app.snapshots import SnapshotStore, publish_once
from app.sources.base import SeriesSource
from app.sources.power import PowerClient
from app.tools.context import ToolContext, last_complete_year


@dataclass
class Services:
    settings: Settings
    cache: Cache
    source: SeriesSource
    today: Callable[[], date] = field(default=date.today)
    operations: Cache | None = None
    planner_busy: bool = False
    planner_limiter: RateLimiter = field(default_factory=lambda: RateLimiter(10))

    def tool_context(self) -> ToolContext:
        """The context for one tool call; the last complete year follows today's date."""
        return ToolContext(
            source=self.source,
            last_complete_year=last_complete_year(self.today()),
            public_base_url=self.settings.public_base_url,
            snapshots=self.cache.snapshots,
        )


def build_services(settings: Settings) -> Services:
    """Open the cache file and a POWER client. Call it inside the running event loop."""
    settings.cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not settings.cache_path.exists() and (DATA_DIR / "cache.sqlite").exists():
        # The shipped seed remains immutable; all refreshes and counters live in state/.
        publish_once(settings.cache_path, (DATA_DIR / "cache.sqlite").read_bytes())
    snapshots = SnapshotStore(settings.snapshot_path)
    cache = Cache(settings.cache_path, snapshots)
    operations = Cache(settings.operational_path)
    return Services(
        settings=settings,
        cache=cache,
        source=PowerClient(cache),
        operations=operations,
        planner_limiter=RateLimiter(settings.ai_rate_per_minute),
    )


async def close_services(services: Services) -> None:
    if isinstance(services.source, PowerClient):
        await services.source.aclose()
    services.cache.close()
    if services.operations is not None:
        services.operations.close()
