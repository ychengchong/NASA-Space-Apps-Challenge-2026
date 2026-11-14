"""Print the verdict for a variable at one to four places (spec 12, stage 1).

    uv run python -m app.cli air_temp 60.17,24.94 --label Helsinki

Like the other adapters, it only translates: the tool layer does every calculation.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from datetime import date
from itertools import zip_longest
from typing import get_args

from app.cache import Cache
from app.catalogue import CatalogueEntry, GridAlignment, get_entry
from app.config import Settings, get_settings
from app.errors import AppError
from app.models import (
    AnalyzeTrendInput,
    ComparePlacesInput,
    Investigation,
    Place,
    PlaceInput,
    PlaceResult,
    Season,
    Trend,
)
from app.sources.power import PowerClient
from app.tools.context import ToolContext, last_complete_year
from app.tools.trends import analyze_trend, compare_places
from app.verdict import caution_text, format_signed_rate

EXIT_ERROR = 1
# p-values are printed with this many significant digits.
P_VALUE_DIGITS = 2

CaseInput = AnalyzeTrendInput | ComparePlacesInput

EPILOG = """\
examples:
  python -m app.cli air_temp 60.17,24.94 --label Helsinki
  python -m app.cli air_temp 60.17,24.94 --from 1991 --to 2020 --season JJA --scan
  python -m app.cli precipitation --label Helsinki --label Nairobi -- 60.17,24.94 -1.29,36.82

When a latitude is negative, put the options first and -- before the places, so the place
is not read as an option.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Print the trend verdict for a catalogue variable at one to four places.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("variable", help="catalogue id, such as air_temp")
    parser.add_argument("places", nargs="+", type=_parse_point, metavar="LAT,LON")
    parser.add_argument(
        "--label", action="append", default=[], metavar="NAME", help="name of each place, in order"
    )
    parser.add_argument("--from", dest="from_", type=int, metavar="YEAR", help="first year")
    parser.add_argument("--to", type=int, metavar="YEAR", help="last year")
    parser.add_argument("--season", choices=get_args(Season), default="annual")
    parser.add_argument("--scan", action="store_true", help="include the period scan")
    return parser


def _parse_point(text: str) -> tuple[float, float]:
    parts = text.split(",")
    try:
        lat, lon = (float(part) for part in parts)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"expected LAT,LON such as 60.17,24.94, got {text!r}"
        ) from error
    return lat, lon


def build_input(args: argparse.Namespace) -> CaseInput:
    """The tool input for the parsed arguments. Raises ValueError when they do not form a case."""
    if len(args.label) > len(args.places):
        raise ValueError("there are more labels than places")
    places = [
        PlaceInput(lat=lat, lon=lon, name=label)
        for (lat, lon), label in zip_longest(args.places, args.label)
    ]
    fields = {
        "variable": args.variable,
        "from": args.from_,
        "to": args.to,
        "season": args.season,
        "scan": args.scan,
    }
    if len(places) == 1:
        return AnalyzeTrendInput.model_validate({**fields, "place": places[0]})
    return ComparePlacesInput.model_validate({**fields, "places": places})


async def run_case(inp: CaseInput, ctx: ToolContext) -> Investigation:
    if isinstance(inp, ComparePlacesInput):
        return await compare_places(inp, ctx)
    return await analyze_trend(inp, ctx)


async def run_with_power(inp: CaseInput, settings: Settings, today: date) -> Investigation:
    """Run the case against NASA POWER through the cache file named in the settings."""
    cache = Cache(settings.cache_path)
    client = PowerClient(cache)
    try:
        ctx = ToolContext(
            source=client,
            last_complete_year=last_complete_year(today),
            public_base_url=settings.public_base_url,
        )
        return await run_case(inp, ctx)
    finally:
        await client.aclose()
        cache.close()


def format_investigation(investigation: Investigation) -> str:
    """The Investigation as plain text: verdicts, summary, key numbers, source, link and steps."""
    entry = get_entry(investigation.variable.id)
    requested = investigation.requested
    lines = [
        f"{entry.name}, {requested.from_} to {requested.to}, {requested.season}"
        f" (case {investigation.id})",
    ]
    for result in investigation.results:
        lines += ["", *_result_lines(entry, result)]
    if investigation.summary is not None:
        lines += ["", f"Summary: {investigation.summary}"]
    lines.append("")
    lines += [
        f"Source: {source.name}, API {source.version}, accessed {source.accessed}"
        for source in investigation.sources
    ]
    lines.append(f"Link: {investigation.app_url}")
    lines += ["", "Steps:"]
    lines += [f"  {number}. {step}" for number, step in enumerate(investigation.steps, start=1)]
    return "\n".join(lines)


def _result_lines(entry: CatalogueEntry, result: PlaceResult) -> list[str]:
    lines = [_cell_line(entry, result.place), f"  {result.verdict.sentence}"]
    if result.trend is not None:
        lines += _trend_lines(entry, result.trend)
    lines += [
        f"  Caution: {caution_text(caution, entry, result.trend)}"
        for caution in result.verdict.cautions
    ]
    return lines


def _cell_line(entry: CatalogueEntry, place: Place) -> str:
    """The place's cell: a MERRA-2 grid point, or the centre of a 1° cell of sunlight and cloud."""
    cell = place.cell
    size = f"{cell.height:g}° by {cell.width:g}°"
    if entry.grid.alignment is GridAlignment.BOUNDED_BY_MULTIPLES:
        return f"{place.name}: {size} cell centred on {cell.lat}, {cell.lon}"
    return f"{place.name}: grid point {cell.lat}, {cell.lon}, cell {size}"


def _trend_lines(entry: CatalogueEntry, trend: Trend) -> list[str]:
    def rate(value: float) -> str:
        return _with_units(format_signed_rate(value, entry.decimals), entry.rate_units)

    lower, upper = trend.sen_ci95
    first, last = trend.line
    return [
        f"  Sen's slope:       {rate(trend.sen_slope)} per decade"
        f" (95% interval {rate(lower)} to {rate(upper)})",
        f"  Total change:      {rate(trend.total_change)}"
        f" from {trend.first_year} to {trend.last_year}",
        f"  Trend line:        {_number(first, entry)} to {_number(last, entry)} {entry.units}",
        f"  Mann-Kendall p:    {trend.mk_p:.{P_VALUE_DIGITS}g}, after the correction factor"
        f" {trend.variance_factor:.2f} (lag-1 autocorrelation {trend.lag1:.2f})",
        f"  Least squares:     {rate(trend.ols_slope)} per decade,"
        f" p {trend.ols_p:.{P_VALUE_DIGITS}g}",
        f"  Years used:        {trend.n}",
    ]


def _number(value: float, entry: CatalogueEntry) -> str:
    return f"{value:.{entry.decimals}f}"


def _with_units(number: str, units: str) -> str:
    return f"{number} {units}" if units else number


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        inp = build_input(args)
    except ValueError as error:
        parser.error(str(error))
    try:
        investigation = asyncio.run(run_with_power(inp, get_settings(), date.today()))
    except AppError as error:
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return EXIT_ERROR
    print(format_investigation(investigation))
    return 0


if __name__ == "__main__":
    sys.exit(main())
