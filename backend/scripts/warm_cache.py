"""Rebuild the pre-warmed cache from data/examples.json and the question bar's suggested prompt
(spec 6, "Caching"; spec 12, "Example cases").

Each case runs through the real tools with a live NASA POWER client, so the cache file ends up
holding every value the cases need, and the committed copy lets the demo open them without
calling NASA. Run from backend/:

    uv run python -m scripts.warm_cache                 # the cache at CACHE_PATH
    uv run python -m scripts.warm_cache --cache PATH

Values already in the cache are not fetched again. The last complete year follows today's date,
as in the running app, so the cached rows are the ones the app will ask for.
"""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from app.adapters.case_query import parse_case_query, parse_query_string
from app.cache import Cache
from app.cli import format_investigation, run_case
from app.config import DATA_DIR, get_settings
from app.errors import AppError
from app.models import Investigation
from app.sources.power import PowerClient
from app.tools.context import ToolContext, last_complete_year

EXAMPLES_PATH = DATA_DIR / "examples.json"
# The question bar suggests "Is Nairobi getting warmer?" (frontend QuestionBar.tsx). This case is
# at the place find_place gives for Nairobi, so the suggested prompt opens from the committed
# cache. A case fetches only the codes on its variable's own grid (fetch_point_series), so these
# MERRA-2 cases warm the MERRA-2 codes alone: sunlight and cloud at their places are not warmed.
SUGGESTED_PROMPT_QUERY = "v=air_temp&p=-1.28,36.82&label=Nairobi"
EXIT_ERROR = 1


def load_example_queries(path: Path = EXAMPLES_PATH) -> list[str]:
    """The case parameter string of every example in `path`, in the file's order."""
    examples = json.loads(path.read_text(encoding="utf-8"))
    return [example["query"] for example in examples]


def load_warm_queries(path: Path = EXAMPLES_PATH) -> list[str]:
    """The case parameter strings the warm-up runs: every example in `path`, then the case of
    the suggested prompt.
    """
    return [*load_example_queries(path), SUGGESTED_PROMPT_QUERY]


async def warm(queries: Sequence[str], ctx: ToolContext) -> list[Investigation]:
    """Run each case through the tools, so the context's source caches the data it needs.

    The cases run one after another, to keep the load on NASA POWER low. Raises `AppError` when
    a query is not a valid case or the source cannot supply data that is not cached.
    """
    investigations: list[Investigation] = []
    for query in queries:
        inp = parse_case_query(parse_query_string(query))
        investigations.append(await run_case(inp, ctx))
    return investigations


async def warm_file(
    queries: Sequence[str], cache_path: Path, today: date, public_base_url: str | None
) -> list[Investigation]:
    """`warm` with a live POWER client that stores what it fetches in the file `cache_path`."""
    cache = Cache(cache_path)
    client = PowerClient(cache)
    try:
        ctx = ToolContext(
            source=client,
            last_complete_year=last_complete_year(today),
            public_base_url=public_base_url,
        )
        return await warm(queries, ctx)
    finally:
        await client.aclose()
        cache.close()


def main(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="python -m scripts.warm_cache",
        description=(
            "Fetch the data of every example case and of the suggested prompt into the cache file."
        ),
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=settings.cache_path,
        help=f"the SQLite file to fill (default: {settings.cache_path})",
    )
    args = parser.parse_args(argv)
    queries = load_warm_queries()
    try:
        investigations = asyncio.run(
            warm_file(queries, args.cache, date.today(), settings.public_base_url)
        )
    except AppError as error:
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return EXIT_ERROR
    print("\n\n".join(format_investigation(investigation) for investigation in investigations))
    print(f"\nCached {len(investigations)} cases in {args.cache}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
