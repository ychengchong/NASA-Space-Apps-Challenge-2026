"""PNG chart of a case (spec 4, "Chart renderer"; spec 9, get_chart; spec 10, /api/chart.png).

The chart draws numbers the tool layer computed and sentences that verdict.py wrote. It
computes no number of its own: Matplotlib's axis ticks are the only numbers chosen here. It
uses the object-oriented Figure API on an Agg canvas and never pyplot, whose global state is
not thread-safe.
"""

import io
import math
from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, ScalarFormatter, StrMethodFormatter

from app.models import Investigation, PlaceResult, Season, SourceRef

# Spec 3, "Wording and accessibility": seasons are named by their months.
SEASON_TITLES: dict[Season, str] = {
    "annual": "every month",
    "DJF": "December to February",
    "MAM": "March to May",
    "JJA": "June to August",
    "SON": "September to November",
}

# The image is FIGURE_WIDTH_PX by FIGURE_HEIGHT_PX pixels.
FIGURE_WIDTH_PX = 1000
FIGURE_HEIGHT_PX = 600
DPI = 100
POINTS_PER_INCH = 72

# Okabe-Ito colours, which stay apart under the common kinds of colour blindness. Each place
# also has its own marker shape, so places never differ by colour alone (spec 3).
PLACE_COLOURS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7")
PLACE_MARKERS = ("o", "s", "^", "D")

TEXT_COLOUR = "#1a1a1a"
MUTED_COLOUR = "#555555"
GRID_COLOUR = "#e3e3e3"
BACKGROUND_COLOUR = "white"

TITLE_FONT_SIZE = 15
SENTENCE_FONT_SIZE = 11
AXIS_LABEL_FONT_SIZE = 10
TICK_FONT_SIZE = 9
LEGEND_FONT_SIZE = 9
FOOTER_FONT_SIZE = 8

SENTENCE_LINE_SPACING = 1.35

# Layout, in pixels from the image edges.
OUTER_MARGIN_PX = 20
TITLE_TOP_PX = 16
SENTENCE_TOP_PX = 50
SENTENCE_TO_AXES_PX = 18
AXES_LEFT_PX = 80
AXES_RIGHT_PX = 24
AXES_BOTTOM_PX = 80
FOOTER_BOTTOM_PX = 12

GRID_LINE_WIDTH = 0.8
LEGEND_FRAME_ALPHA = 0.9
VALUE_LINE_WIDTH = 1.4
VALUE_MARKER_SIZE = 5
TREND_LINE_WIDTH = 2.2
TREND_LINE_STYLE = "--"
# Empty space at each end of the year axis, in years, so the first and last markers show whole.
YEAR_AXIS_MARGIN = 0.5

TREND_LEGEND_LABEL = "Trend line"
DATA_CREDIT = "Data:"


def render_case_png(investigation: Investigation) -> bytes:
    """Return a PNG chart of the case, FIGURE_WIDTH_PX by FIGURE_HEIGHT_PX pixels.

    The chart is that of `case_figure`. The file carries no software or time metadata, so the
    same investigation always gives the same bytes.
    """
    figure = case_figure(investigation)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=DPI, metadata={"Software": None})
    return buffer.getvalue()


def case_figure(investigation: Investigation) -> Figure:
    """Return the chart of the case as a Matplotlib Figure on an Agg canvas.

    Each place gets its yearly values, joined by a line with its own colour and marker; a
    missing year stays a gap and is never drawn as zero. A place with a trend also gets a
    dashed trend line from the trend's first to its last year, at the values in `trend.line`.
    A place with too few years or no data shows only the values it has, with no trend line.
    Above the chart are the title (variable, years and season) and, wrapped under it, the
    comparison summary or, for one place, its verdict sentence. The footer names the data
    source, its version and the access date. Every text is drawn as plain text.
    """
    figure = Figure(
        figsize=(FIGURE_WIDTH_PX / DPI, FIGURE_HEIGHT_PX / DPI),
        dpi=DPI,
        facecolor=BACKGROUND_COLOUR,
    )
    canvas = FigureCanvasAgg(figure)
    sentence_lines = _wrap(_headline(investigation), canvas)
    _draw_title(figure, investigation)
    _draw_sentence(figure, sentence_lines)
    axes = figure.add_axes(_axes_rect(len(sentence_lines)))
    value_lines = [
        _draw_place(axes, result, index) for index, result in enumerate(investigation.results)
    ]
    _style_axes(axes, investigation)
    _draw_legend(axes, investigation.results, value_lines)
    _draw_footer(figure, investigation.sources)
    return figure


def _headline(investigation: Investigation) -> str | None:
    """The comparison summary, or the verdict sentence when the case has one place."""
    if investigation.summary is not None:
        return investigation.summary
    if len(investigation.results) == 1:
        return investigation.results[0].verdict.sentence
    return None


def _sentence_font() -> FontProperties:
    return FontProperties(size=SENTENCE_FONT_SIZE)


def _wrap(sentence: str | None, canvas: FigureCanvasAgg) -> list[str]:
    """Split the sentence into lines between words that each fit the image width.

    Widths are measured in the sentence's font, since a count of characters cannot tell a
    narrow name from a wide one. A word wider than a whole line gets a line of its own.
    """
    if sentence is None:
        return []
    renderer = canvas.get_renderer()
    font = _sentence_font()
    max_width_px = FIGURE_WIDTH_PX - 2 * OUTER_MARGIN_PX
    lines: list[str] = []
    line = ""
    for word in sentence.split():
        candidate = f"{line} {word}" if line else word
        width_px, _, _ = renderer.get_text_width_height_descent(candidate, font, ismath=False)
        if line and width_px > max_width_px:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def _title(investigation: Investigation) -> str:
    requested = investigation.requested
    return (
        f"{investigation.variable.name}, {requested.from_} to {requested.to}, "
        f"{SEASON_TITLES[requested.season]}"
    )


def _draw_title(figure: Figure, investigation: Investigation) -> None:
    figure.text(
        OUTER_MARGIN_PX / FIGURE_WIDTH_PX,
        1 - TITLE_TOP_PX / FIGURE_HEIGHT_PX,
        _title(investigation),
        ha="left",
        va="top",
        fontsize=TITLE_FONT_SIZE,
        fontweight="bold",
        color=TEXT_COLOUR,
        parse_math=False,
    )


def _draw_sentence(figure: Figure, lines: Sequence[str]) -> None:
    if not lines:
        return
    figure.text(
        OUTER_MARGIN_PX / FIGURE_WIDTH_PX,
        1 - SENTENCE_TOP_PX / FIGURE_HEIGHT_PX,
        "\n".join(lines),
        ha="left",
        va="top",
        fontproperties=_sentence_font(),
        linespacing=SENTENCE_LINE_SPACING,
        color=TEXT_COLOUR,
        parse_math=False,
    )


def _axes_rect(sentence_line_count: int) -> tuple[float, float, float, float]:
    """Left, bottom, width and height of the plot area, as fractions of the image."""
    line_height_px = SENTENCE_FONT_SIZE * SENTENCE_LINE_SPACING * DPI / POINTS_PER_INCH
    top_px = SENTENCE_TOP_PX + sentence_line_count * line_height_px + SENTENCE_TO_AXES_PX
    width_px = FIGURE_WIDTH_PX - AXES_LEFT_PX - AXES_RIGHT_PX
    height_px = FIGURE_HEIGHT_PX - AXES_BOTTOM_PX - top_px
    return (
        AXES_LEFT_PX / FIGURE_WIDTH_PX,
        AXES_BOTTOM_PX / FIGURE_HEIGHT_PX,
        width_px / FIGURE_WIDTH_PX,
        height_px / FIGURE_HEIGHT_PX,
    )


def _draw_place(axes: Axes, result: PlaceResult, index: int) -> Line2D:
    """Draw the yearly values and trend line of the place at `index`; return the line of values."""
    colour = PLACE_COLOURS[index % len(PLACE_COLOURS)]
    years = [year_value.year for year_value in result.series]
    # NaN, never zero, so Matplotlib leaves a gap where a year has no value.
    values = [
        math.nan if year_value.value is None else year_value.value for year_value in result.series
    ]
    (value_line,) = axes.plot(
        years,
        values,
        color=colour,
        marker=PLACE_MARKERS[index % len(PLACE_MARKERS)],
        markersize=VALUE_MARKER_SIZE,
        linewidth=VALUE_LINE_WIDTH,
        linestyle="-",
    )
    trend = result.trend
    if trend is not None:
        axes.plot(
            [trend.first_year, trend.last_year],
            list(trend.line),
            color=colour,
            linewidth=TREND_LINE_WIDTH,
            linestyle=TREND_LINE_STYLE,
        )
    return value_line


def _style_axes(axes: Axes, investigation: Investigation) -> None:
    requested = investigation.requested
    variable = investigation.variable
    axes.set_facecolor(BACKGROUND_COLOUR)
    axes.set_xlim(requested.from_ - YEAR_AXIS_MARGIN, requested.to + YEAR_AXIS_MARGIN)
    axes.xaxis.set_major_locator(MaxNLocator(integer=True))
    axes.xaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
    axes.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    if not _has_values(investigation.results):
        # Without values the y-axis would show Matplotlib's default 0 to 1, which no data gave.
        axes.set_yticks([])
    axes.set_xlabel("Year", fontsize=AXIS_LABEL_FONT_SIZE, color=TEXT_COLOUR, parse_math=False)
    axes.set_ylabel(
        f"{variable.name} ({variable.units})",
        fontsize=AXIS_LABEL_FONT_SIZE,
        color=TEXT_COLOUR,
        parse_math=False,
    )
    axes.tick_params(labelsize=TICK_FONT_SIZE, colors=MUTED_COLOUR)
    axes.grid(axis="y", color=GRID_COLOUR, linewidth=GRID_LINE_WIDTH)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(MUTED_COLOUR)


def _has_values(results: Sequence[PlaceResult]) -> bool:
    return any(year_value.value is not None for result in results for year_value in result.series)


def _draw_legend(axes: Axes, results: Sequence[PlaceResult], value_lines: Sequence[Line2D]) -> None:
    handles: list[Line2D] = list(value_lines)
    # Explicit labels, so a place name that starts with "_" is still listed.
    labels = [result.place.name for result in results]
    if any(result.trend is not None for result in results):
        handles.append(
            Line2D(
                [],
                [],
                color=MUTED_COLOUR,
                linewidth=TREND_LINE_WIDTH,
                linestyle=TREND_LINE_STYLE,
            )
        )
        labels.append(TREND_LEGEND_LABEL)
    legend = axes.legend(
        handles,
        labels,
        loc="best",
        fontsize=LEGEND_FONT_SIZE,
        frameon=True,
        framealpha=LEGEND_FRAME_ALPHA,
        edgecolor=GRID_COLOUR,
        labelcolor=TEXT_COLOUR,
    )
    for text in legend.get_texts():
        text.set_parse_math(False)


def _footer(sources: Sequence[SourceRef]) -> str | None:
    if not sources:
        return None
    credits = [
        f"{source.name}, API {source.version}, accessed {source.accessed}" for source in sources
    ]
    return f"{DATA_CREDIT} {'; '.join(credits)}"


def _draw_footer(figure: Figure, sources: Sequence[SourceRef]) -> None:
    footer = _footer(sources)
    if footer is None:
        return
    figure.text(
        OUTER_MARGIN_PX / FIGURE_WIDTH_PX,
        FOOTER_BOTTOM_PX / FIGURE_HEIGHT_PX,
        footer,
        ha="left",
        va="bottom",
        fontsize=FOOTER_FONT_SIZE,
        color=MUTED_COLOUR,
        parse_math=False,
    )
