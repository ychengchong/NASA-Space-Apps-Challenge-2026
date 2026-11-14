"""Build the frozen whole-world mean series (spec 7, "The whole world") from a fixed sample.

The sample is every 20° of latitude from 80°S to 80°N and every 20° of longitude from 180°W:
162 points, each read on the grid of every variable, the way a case reads a place. The world
mean of a variable is the cosine-of-latitude weighted mean of its sample cells for each month,
with the fixed footprint of an area mean: a month is missing when any cell is missing. Only
variables marked `world_mean` in the catalogue are written; land-only and sea-only ones are not.

Run from backend/:

    uv run python -m scripts.build_world_mean
    uv run python -m scripts.build_world_mean --cache PATH --output PATH --limit N

Every point fetched is kept in the cache file, so a rerun asks NASA POWER only for the points
it does not hold yet: the build can be stopped and resumed. One point costs one call per grid.
"""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from app.cache import Cache
from app.catalogue import CatalogueEntry, GridSize, load_catalogue
from app.config import BACKEND_DIR, DATA_DIR
from app.errors import AppError
from app.models import PlaceInput
from app.sources.base import PointSeries
from app.sources.power import PowerClient
from app.stats import cos_lat_weighted_mean
from app.tools.context import last_complete_year
from app.tools.places import resolve_place

WORLD_MEAN_PATH = DATA_DIR / "world-mean.json"
DEFAULT_CACHE_PATH = BACKEND_DIR.parent / "state" / "world-sample.sqlite"
SCHEMA = "world_mean_v1"
# Spec 7, "The whole world": the sample's spacing in degrees and its rows and columns.
SAMPLE_STEP_DEGREES = 20
SAMPLE_LATITUDES = tuple(range(-80, 81, SAMPLE_STEP_DEGREES))
SAMPLE_LONGITUDES = tuple(range(-180, 180, SAMPLE_STEP_DEGREES))
# Points fetched at the same time; the POWER client allows two calls at once.
CONCURRENT_POINTS = 2
EXIT_ERROR = 1

# (grid, cell latitude, cell longitude) -> the series of every catalogue code on that grid.
SampleSeries = dict[tuple[GridSize, float, float], dict[str, PointSeries]]


def sample_points() -> list[tuple[float, float]]:
    """The sample's points as (lat, lon), south to north, then west to east."""
    return [(float(lat), float(lon)) for lat in SAMPLE_LATITUDES for lon in SAMPLE_LONGITUDES]


def world_entries() -> list[CatalogueEntry]:
    return [entry for entry in load_catalogue() if entry.world_mean]


def grids() -> list[GridSize]:
    """The grids of the world-mean variables, in catalogue order, each once."""
    return list(dict.fromkeys(entry.grid for entry in world_entries()))


async def fetch_sample(
    client: PowerClient, points: Sequence[tuple[float, float]], end_year: int
) -> SampleSeries:
    """Every catalogue code on each world-mean grid at every point's cell, through `client`.

    Each grid's codes go in one call, as fetch_point_series asks for them, so rows cached here
    are the rows a case at the same cell would read. Raises `SourceUnavailableError` when a cell
    is neither cached nor available.
    """
    catalogue = load_catalogue()
    limit = asyncio.Semaphore(CONCURRENT_POINTS)
    found: SampleSeries = {}
    done = 0

    async def fetch(lat: float, lon: float) -> None:
        nonlocal done
        async with limit:
            for grid in grids():
                entry = next(item for item in catalogue if item.grid == grid)
                cell = resolve_place(PlaceInput(lat=lat, lon=lon), entry).cell
                codes = [item.code for item in catalogue if item.grid == grid]
                found[(grid, cell.lat, cell.lon)] = await client.point_series(
                    cell.lat, cell.lon, codes, end_year
                )
        done += 1
        if done % 10 == 0 or done == len(points):
            print(f"{done} of {len(points)} points", file=sys.stderr, flush=True)

    await asyncio.gather(*(fetch(lat, lon) for lat, lon in points))
    return found


def world_means(
    sample: SampleSeries, points: Sequence[tuple[float, float]]
) -> dict[str, dict[str, float | None]]:
    """Each world-mean variable's monthly world mean, keyed "YYYY-MM", in the variable's units.

    Each sample cell is weighted by the cosine of its latitude, and a month is missing when any
    cell lacks it (`cos_lat_weighted_mean`).
    """
    means: dict[str, dict[str, float | None]] = {}
    for entry in world_entries():
        cells = []
        for lat, lon in points:
            cell = resolve_place(PlaceInput(lat=lat, lon=lon), entry).cell
            cells.append((cell.lat, sample[(entry.grid, cell.lat, cell.lon)][entry.code].monthly))
        monthly = cos_lat_weighted_mean(cells)
        means[entry.id] = {
            f"{year:04d}-{month:02d}": value for (year, month), value in sorted(monthly.items())
        }
    return means


def world_document(
    sample: SampleSeries, points: Sequence[tuple[float, float]], end_year: int, built: date
) -> dict[str, Any]:
    """The frozen file: how the sample was drawn, where its values came from, and the means."""
    series = [item for codes in sample.values() for item in codes.values()]
    return {
        "schema": SCHEMA,
        "built": built.isoformat(),
        "end_year": end_year,
        "sample": {
            "step_degrees": SAMPLE_STEP_DEGREES,
            "latitudes": list(SAMPLE_LATITUDES),
            "longitudes": list(SAMPLE_LONGITUDES),
            "points": len(points),
        },
        "api_versions": sorted({item.version for item in series}),
        "accessed": sorted({item.accessed for item in series}),
        "variables": world_means(sample, points),
    }


async def build(cache_path: Path, output: Path, today: date, limit: int | None) -> int:
    points = sample_points()[:limit] if limit else sample_points()
    end_year = last_complete_year(today)
    cache = Cache(cache_path)
    client = PowerClient(cache, today=lambda: today)
    try:
        sample = await fetch_sample(client, points, end_year)
    finally:
        await client.aclose()
        cache.close()
    if limit is None:
        document = world_document(sample, points, end_year, today)
        output.write_text(
            json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {output} from {len(points)} points", file=sys.stderr)
    return len(points)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.build_world_mean",
        description="Fetch the world-mean sample (resumable) and write the frozen world means.",
    )
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--output", type=Path, default=WORLD_MEAN_PATH)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="fetch only the first N points and write nothing (a trial run)",
    )
    args = parser.parse_args(argv)
    try:
        asyncio.run(build(args.cache, args.output, date.today(), args.limit))
    except AppError as error:
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return EXIT_ERROR
    return 0


if __name__ == "__main__":
    sys.exit(main())
