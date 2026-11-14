"""The long-lived objects the adapters share: settings, the cache and the data source."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from app.cache import Cache
from app.config import Settings
from app.sources.base import SeriesSource
from app.sources.power import PowerClient
from app.tools.context import ToolContext, last_complete_year


@dataclass
class Services:
    settings: Settings
    cache: Cache
    source: SeriesSource
    today: Callable[[], date] = field(default=date.today)

    def tool_context(self) -> ToolContext:
        """The context for one tool call; the last complete year follows today's date."""
        return ToolContext(
            source=self.source,
            last_complete_year=last_complete_year(self.today()),
            public_base_url=self.settings.public_base_url,
        )


def build_services(settings: Settings) -> Services:
    """Open the cache file and a POWER client. Call it inside the running event loop."""
    cache = Cache(settings.cache_path)
    return Services(settings=settings, cache=cache, source=PowerClient(cache))


async def close_services(services: Services) -> None:
    if isinstance(services.source, PowerClient):
        await services.source.aclose()
    services.cache.close()
