"""The example cases of spec 12 open from the committed cache alone.

Spec 2: "A pre-loaded example opens without any call to NASA." The examples run through the real
POWER client on a copy of data/cache.sqlite, with an HTTP transport that fails every request. The
whole warm-up of scripts/warm_cache.py runs the same way.
"""

import json
import re
import shutil
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters.case_query import parse_case_query, parse_query_string
from app.cache import Cache
from app.catalogue import get_entry, load_catalogue
from app.config import DATA_DIR
from app.models import (
    AnalyzeTrendInput,
    ComparePlacesInput,
    FindPlaceInput,
    Investigation,
)
from app.sources.power import PowerClient
from app.tools.context import ToolContext
from app.tools.places import find_place, snap_to_grid
from app.tools.trends import CASE_PATH
from scripts.warm_cache import (
    EXAMPLES_PATH,
    SUGGESTED_PROMPT_QUERY,
    load_example_queries,
    load_warm_queries,
    warm,
)

COMMITTED_CACHE = DATA_DIR / "cache.sqlite"
# The committed cache was fetched up to this year; passed in rather than read from the clock.
LAST_COMPLETE_YEAR = 2025
# Spec 10: /api/examples returns a list of { title, teaser, query }.
EXAMPLE_FIELDS = {"title", "teaser", "query"}
# Spec 12, "Example cases": the idea each example teaches, in the order of examples.json.
CLEAR_TREND, NOT_SIGNIFICANT, COMPARISON = range(3)
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

EXAMPLES: list[dict[str, Any]] = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
QUERIES = [example["query"] for example in EXAMPLES]


class NoNetwork:
    """An HTTP transport handler that records every request and fails it."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        raise httpx.ConnectError("the examples must not call NASA POWER", request=request)


async def warm_offline(
    tmp_path: Path, queries: Sequence[str]
) -> tuple[list[Investigation], list[httpx.Request]]:
    """Each query's Investigation from a copy of the committed cache, and the requests sent."""
    cache_copy = tmp_path / "cache.sqlite"
    shutil.copyfile(COMMITTED_CACHE, cache_copy)
    network = NoNetwork()
    cache = Cache(cache_copy)
    http = httpx.AsyncClient(transport=httpx.MockTransport(network))
    try:
        ctx = ToolContext(source=PowerClient(cache, http), last_complete_year=LAST_COMPLETE_YEAR)
        investigations = await warm(queries, ctx)
    finally:
        await http.aclose()
        cache.close()
    return investigations, network.requests


async def run_examples_offline(tmp_path: Path) -> tuple[list[Investigation], list[httpx.Request]]:
    """Every example's Investigation from a copy of the committed cache, and the requests sent."""
    return await warm_offline(tmp_path, load_example_queries())


def committed_rows(tmp_path: Path) -> set[tuple[float, float, str]]:
    """The (lat, lon, code) of every row in the committed cache, read from a copy."""
    cache_copy = tmp_path / "committed.sqlite"
    shutil.copyfile(COMMITTED_CACHE, cache_copy)
    connection = sqlite3.connect(cache_copy)
    try:
        rows = connection.execute("SELECT lat, lon, code FROM point_series").fetchall()
    finally:
        connection.close()
    return {(lat, lon, code) for lat, lon, code in rows}


def committed_grid_points(tmp_path: Path) -> set[tuple[float, float]]:
    """The grid points that the committed cache holds rows for."""
    return {(lat, lon) for lat, lon, _ in committed_rows(tmp_path)}


def warmed_rows(investigations: Sequence[Investigation]) -> set[tuple[float, float, str]]:
    """The rows the warm-up writes: every code on the analysed variable's grid at each cell."""
    rows: set[tuple[float, float, str]] = set()
    for investigation in investigations:
        grid = get_entry(investigation.variable.id).grid
        codes = [entry.code for entry in load_catalogue() if entry.grid == grid]
        for result in investigation.results:
            rows.update((result.place.cell.lat, result.place.cell.lon, code) for code in codes)
    return rows


def grid_points(investigations: Sequence[Investigation]) -> set[tuple[float, float]]:
    return {
        (result.place.cell.lat, result.place.cell.lon)
        for investigation in investigations
        for result in investigation.results
    }


def test_examples_file_lists_three_cases_with_title_teaser_and_query() -> None:
    assert len(EXAMPLES) == 3
    for example in EXAMPLES:
        assert set(example) == EXAMPLE_FIELDS
        assert all(isinstance(text, str) and text.strip() for text in example.values())


@pytest.mark.parametrize("query", QUERIES)
def test_example_query_parses_with_its_period_and_season_fixed(query: str) -> None:
    parameters = parse_query_string(query)
    inp = parse_case_query(parameters)

    assert inp.from_ is not None
    assert inp.to is not None
    assert "s" in parameters


def test_two_examples_have_one_place_and_the_comparison_has_two() -> None:
    inputs = [parse_case_query(parse_query_string(query)) for query in QUERIES]

    assert isinstance(inputs[CLEAR_TREND], AnalyzeTrendInput)
    assert isinstance(inputs[NOT_SIGNIFICANT], AnalyzeTrendInput)
    assert isinstance(inputs[COMPARISON], ComparePlacesInput)
    assert len(inputs[COMPARISON].places) == 2


@pytest.mark.parametrize("example", EXAMPLES, ids=[example["title"] for example in EXAMPLES])
def test_example_text_holds_no_number_except_years_of_its_period(example: dict[str, Any]) -> None:
    # Every number a user sees comes from the analysis, so the text may name years only.
    inp = parse_case_query(parse_query_string(example["query"]))
    numbers = NUMBER.findall(f"{example['title']} {example['teaser']}")

    for number in numbers:
        assert number.isdigit()
        assert inp.from_ is not None and inp.to is not None
        assert inp.from_ <= int(number) <= inp.to


@pytest.mark.anyio
async def test_every_example_answers_from_the_committed_cache_without_calling_nasa(
    tmp_path: Path,
) -> None:
    investigations, requests = await run_examples_offline(tmp_path)

    assert len(investigations) == len(EXAMPLES)
    assert requests == []


@pytest.mark.anyio
async def test_example_query_is_the_link_the_backend_builds(tmp_path: Path) -> None:
    investigations, _ = await run_examples_offline(tmp_path)

    assert [investigation.app_url for investigation in investigations] == [
        f"{CASE_PATH}?{query}" for query in QUERIES
    ]


@pytest.mark.anyio
async def test_clear_trend_example_is_significant_and_not_borderline(tmp_path: Path) -> None:
    investigations, _ = await run_examples_offline(tmp_path)
    (result,) = investigations[CLEAR_TREND].results

    assert result.verdict.kind == "significant"
    assert "borderline" not in result.verdict.cautions


@pytest.mark.anyio
async def test_not_significant_example_is_not_significant_and_not_borderline(
    tmp_path: Path,
) -> None:
    investigations, _ = await run_examples_offline(tmp_path)
    (result,) = investigations[NOT_SIGNIFICANT].results

    assert result.verdict.kind == "not_significant"
    assert "borderline" not in result.verdict.cautions


@pytest.mark.anyio
async def test_comparison_example_tests_a_trend_at_both_places(tmp_path: Path) -> None:
    # The pair was fixed before any result was seen, so only the shape of the answer is checked.
    investigations, _ = await run_examples_offline(tmp_path)
    comparison = investigations[COMPARISON]

    assert len(comparison.results) == 2
    assert all(result.trend is not None for result in comparison.results)
    assert comparison.contrast is not None
    assert comparison.summary is not None


# The warm-up (spec 6, "Caching") reads only rows the committed cache holds, and the committed
# cache holds exactly the rows a rebuild writes, so it carries no row that no case reads.


@pytest.mark.anyio
async def test_warm_up_runs_from_the_committed_cache_without_calling_nasa(tmp_path: Path) -> None:
    _, requests = await warm_offline(tmp_path, load_warm_queries())

    assert requests == []


@pytest.mark.anyio
async def test_warm_up_covers_every_grid_point_of_the_committed_cache(tmp_path: Path) -> None:
    investigations, _ = await warm_offline(tmp_path, load_warm_queries())

    assert grid_points(investigations) == committed_grid_points(tmp_path)


@pytest.mark.anyio
async def test_committed_cache_holds_exactly_the_rows_a_rebuild_writes(tmp_path: Path) -> None:
    investigations, _ = await warm_offline(tmp_path, load_warm_queries())

    assert committed_rows(tmp_path) == warmed_rows(investigations)


def test_suggested_prompt_case_is_at_the_grid_point_of_nairobi_as_find_place_gives_it() -> None:
    # The question bar suggests "Is Nairobi getting warmer?"; find_place resolves its place.
    inp = parse_case_query(parse_query_string(SUGGESTED_PROMPT_QUERY))
    nairobi = find_place(FindPlaceInput(query="Nairobi"))[0]

    assert isinstance(inp, AnalyzeTrendInput)
    assert snap_to_grid(inp.place.lat, inp.place.lon) == snap_to_grid(nairobi.lat, nairobi.lon)
