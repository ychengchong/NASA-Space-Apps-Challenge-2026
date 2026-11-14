"""The chart renderer (spec 4, "Chart renderer"): a PNG of a case, drawn from its Investigation."""

import struct
from typing import Any

import anyio
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from app.models import AnalyzeTrendInput, ComparePlacesInput, Investigation, PlaceInput
from app.render import (
    FIGURE_HEIGHT_PX,
    FIGURE_WIDTH_PX,
    TREND_LEGEND_LABEL,
    case_figure,
    render_case_png,
)
from app.sources.base import MonthlyValues
from app.tools.context import ToolContext
from app.tools.places import snap_to_grid
from app.tools.trends import analyze_trend, compare_places
from tests.fake_source import FAKE_ACCESSED, FAKE_VERSION, FakeSource, line, monthly_from_yearly

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# PNG chunks that hold text or a timestamp, such as Matplotlib's "Software" entry.
METADATA_CHUNKS = {b"tEXt", b"iTXt", b"zTXt", b"tIME"}
LAST_COMPLETE_YEAR = 2025
GAP_YEAR = 2000

HELSINKI = PlaceInput(lat=60.17, lon=24.94, name="Helsinki")
NAIROBI = PlaceInput(lat=-1.29, lon=36.82, name="Nairobi")

RISING_WITH_GAP = monthly_from_yearly({**line(0.05), GAP_YEAR: None})
FALLING = monthly_from_yearly(line(-0.05))
ALL_MISSING = monthly_from_yearly(dict.fromkeys(range(1981, LAST_COMPLETE_YEAR + 1), None))


def context(source: FakeSource) -> ToolContext:
    return ToolContext(source=source, last_complete_year=LAST_COMPLETE_YEAR)


def analyse(monthly: MonthlyValues, place: PlaceInput = HELSINKI, **fields: Any) -> Investigation:
    inp = AnalyzeTrendInput.model_validate({"variable": "air_temp", "place": place, **fields})
    return anyio.run(analyze_trend, inp, context(FakeSource(monthly)))


def compare_helsinki_and_nairobi() -> Investigation:
    source = FakeSource(
        by_point={
            snap_to_grid(HELSINKI.lat, HELSINKI.lon): RISING_WITH_GAP,
            snap_to_grid(NAIROBI.lat, NAIROBI.lon): FALLING,
        }
    )
    inp = ComparePlacesInput.model_validate({"variable": "air_temp", "places": [HELSINKI, NAIROBI]})
    return anyio.run(compare_places, inp, context(source))


def only_axes(figure: Figure) -> Axes:
    (axes,) = figure.axes
    return axes


def value_lines(figure: Figure) -> list[Line2D]:
    return [drawn for drawn in only_axes(figure).get_lines() if drawn.get_linestyle() == "-"]


def trend_lines(figure: Figure) -> list[Line2D]:
    return [drawn for drawn in only_axes(figure).get_lines() if drawn.get_linestyle() == "--"]


def legend_labels(figure: Figure) -> list[str]:
    legend = only_axes(figure).get_legend()
    assert legend is not None
    return [text.get_text() for text in legend.get_texts()]


def figure_texts(figure: Figure) -> list[str]:
    """The texts drawn on the figure itself, outside the plot, with line breaks as spaces."""
    return [text.get_text().replace("\n", " ") for text in figure.texts]


def chunk_types(png: bytes) -> list[bytes]:
    types: list[bytes] = []
    position = len(PNG_SIGNATURE)
    while position < len(png):
        (length,) = struct.unpack(">I", png[position : position + 4])
        types.append(png[position + 4 : position + 8])
        # Length, type and checksum take 12 bytes around the chunk's data.
        position += length + 12
    return types


# The PNG file


def test_png_starts_with_the_png_signature() -> None:
    assert render_case_png(analyse(RISING_WITH_GAP)).startswith(PNG_SIGNATURE)


def test_png_is_1000_by_600_pixels() -> None:
    png = render_case_png(analyse(RISING_WITH_GAP))

    # The IHDR chunk comes first; its data opens with the width and the height.
    width, height = struct.unpack(">II", png[16:24])

    assert (width, height) == (FIGURE_WIDTH_PX, FIGURE_HEIGHT_PX)


def test_same_investigation_gives_identical_png_bytes() -> None:
    investigation = compare_helsinki_and_nairobi()

    assert render_case_png(investigation) == render_case_png(investigation)


def test_png_carries_no_text_or_time_metadata() -> None:
    png = render_case_png(analyse(RISING_WITH_GAP))

    assert METADATA_CHUNKS.isdisjoint(chunk_types(png))


def test_two_places_render_to_a_png() -> None:
    assert render_case_png(compare_helsinki_and_nairobi()).startswith(PNG_SIGNATURE)


def test_too_few_years_renders_to_a_png() -> None:
    investigation = analyse(RISING_WITH_GAP, **{"from": 2020})
    assert investigation.results[0].verdict.kind == "too_few_years"

    assert render_case_png(investigation).startswith(PNG_SIGNATURE)


def test_all_missing_renders_to_a_png() -> None:
    investigation = analyse(ALL_MISSING)
    assert investigation.results[0].verdict.kind == "no_data"

    assert render_case_png(investigation).startswith(PNG_SIGNATURE)


# What the chart draws


def test_one_place_draws_its_values_and_a_dashed_trend_line() -> None:
    figure = case_figure(analyse(RISING_WITH_GAP))

    assert (len(value_lines(figure)), len(trend_lines(figure))) == (1, 1)


def test_trend_line_runs_from_first_to_last_year_at_the_line_values() -> None:
    investigation = analyse(RISING_WITH_GAP)
    trend = investigation.results[0].trend
    assert trend is not None

    (trend_line,) = trend_lines(case_figure(investigation))

    assert list(trend_line.get_xdata()) == [trend.first_year, trend.last_year]
    assert list(trend_line.get_ydata()) == list(trend.line)


def test_missing_year_is_a_gap_and_not_zero() -> None:
    (values,) = value_lines(case_figure(analyse(RISING_WITH_GAP)))
    years = list(values.get_xdata())

    plotted = np.asarray(values.get_ydata(), dtype=float)

    assert np.isnan(plotted[years.index(GAP_YEAR)])


def test_each_place_has_its_own_colour_and_marker() -> None:
    lines = value_lines(case_figure(compare_helsinki_and_nairobi()))

    colours = {drawn.get_color() for drawn in lines}
    markers = {drawn.get_marker() for drawn in lines}

    assert (len(colours), len(markers)) == (2, 2)


def test_too_few_years_draws_the_values_without_a_trend_line() -> None:
    figure = case_figure(analyse(RISING_WITH_GAP, **{"from": 2020}))

    assert (len(value_lines(figure)), len(trend_lines(figure))) == (1, 0)


def test_no_data_draws_no_trend_line() -> None:
    assert trend_lines(case_figure(analyse(ALL_MISSING))) == []


def test_no_data_leaves_the_value_axis_without_ticks() -> None:
    assert list(only_axes(case_figure(analyse(ALL_MISSING))).get_yticks()) == []


def test_year_axis_spans_the_requested_years() -> None:
    left, right = only_axes(case_figure(analyse(RISING_WITH_GAP, **{"from": 1990}))).get_xlim()

    assert left < 1990 < right and left < LAST_COMPLETE_YEAR < right


# Text


def test_title_names_the_variable_years_and_season_months() -> None:
    investigation = analyse(RISING_WITH_GAP, **{"from": 1990, "to": 2020, "season": "DJF"})

    title = figure_texts(case_figure(investigation))[0]

    assert title == "Air temperature, 1990 to 2020, December to February"


def test_annual_title_reads_every_month() -> None:
    title = figure_texts(case_figure(analyse(RISING_WITH_GAP, **{"from": 1990, "to": 2020})))[0]

    assert title == "Air temperature, 1990 to 2020, every month"


def test_one_place_shows_its_verdict_sentence_under_the_title() -> None:
    investigation = analyse(RISING_WITH_GAP)

    assert investigation.results[0].verdict.sentence in figure_texts(case_figure(investigation))


def test_comparison_shows_the_summary_sentence_under_the_title() -> None:
    investigation = compare_helsinki_and_nairobi()
    assert investigation.summary is not None

    assert investigation.summary in figure_texts(case_figure(investigation))


def test_long_sentence_wraps_onto_several_lines() -> None:
    long_name = PlaceInput(lat=60.17, lon=24.94, name="W" * 40)
    figure = case_figure(analyse(RISING_WITH_GAP, place=long_name, **{"from": 1990}))

    sentence = figure.texts[1].get_text()

    assert sentence.count("\n") >= 1


def test_legend_lists_the_place_names_and_the_trend_line() -> None:
    labels = legend_labels(case_figure(compare_helsinki_and_nairobi()))

    assert labels == ["Helsinki", "Nairobi", TREND_LEGEND_LABEL]


def test_dollar_signs_in_a_place_name_are_drawn_as_plain_text() -> None:
    # Read as Matplotlib's maths notation, "$^$" would fail to draw.
    dollar_name = PlaceInput(lat=60.17, lon=24.94, name="Peak $^$ camp")

    assert render_case_png(analyse(RISING_WITH_GAP, place=dollar_name)).startswith(PNG_SIGNATURE)


def test_place_name_starting_with_underscore_is_in_the_legend() -> None:
    # Matplotlib leaves such a label out of a legend unless the labels are given explicitly.
    underscore_name = PlaceInput(lat=60.17, lon=24.94, name="_Camp")

    labels = legend_labels(case_figure(analyse(RISING_WITH_GAP, place=underscore_name)))

    assert labels[0] == "_Camp"


def test_value_axis_label_names_the_variable_and_its_units() -> None:
    assert only_axes(case_figure(analyse(RISING_WITH_GAP))).get_ylabel() == "Air temperature (°C)"


def test_footer_credits_the_source_with_its_version_and_access_date() -> None:
    footer = figure_texts(case_figure(analyse(RISING_WITH_GAP)))[-1]

    assert footer == f"Data: NASA POWER (MERRA-2), API {FAKE_VERSION}, accessed {FAKE_ACCESSED}"
