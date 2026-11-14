"""Builds the app for the REST and app tests: injected services, a fixed date, no network."""

from dataclasses import replace
from datetime import date
from pathlib import Path

from app.cache import Cache
from app.config import load_settings
from app.services import Services
from app.sources.base import SeriesSource

# On this date the last complete year is 2025.
TODAY = date(2026, 11, 13)
BASE_URL = "https://trend.example"
GENEROUS_RATE_LIMIT = 10_000

INDEX_HTML = "<!doctype html><title>Trend Detective</title>"
ASSET_PATH = "assets/app.js"
ASSET_JS = "console.log('app');"


def make_services(
    cache: Cache, source: SeriesSource, rate_limit_per_minute: int = GENEROUS_RATE_LIMIT
) -> Services:
    settings = replace(
        load_settings(), public_base_url=BASE_URL, rate_limit_per_minute=rate_limit_per_minute
    )
    return Services(settings=settings, cache=cache, source=source, today=lambda: TODAY)


def write_web_app(directory: Path) -> Path:
    """A stand-in for the built frontend: index.html and one asset file."""
    (directory / ASSET_PATH).parent.mkdir(parents=True)
    (directory / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (directory / ASSET_PATH).write_text(ASSET_JS, encoding="utf-8")
    return directory
