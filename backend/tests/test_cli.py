import pytest

from app.cli import build_input, build_parser, format_investigation, main, run_case
from app.models import AnalyzeTrendInput, ComparePlacesInput
from app.tools.context import ToolContext
from tests.fake_source import FakeSource, line, monthly_from_yearly

LAST_COMPLETE_YEAR = 2025
RISING = monthly_from_yearly(line(0.05))


def parse(*argv: str) -> AnalyzeTrendInput | ComparePlacesInput:
    return build_input(build_parser().parse_args(argv))


def test_one_place_builds_an_analyze_trend_input() -> None:
    inp = parse("air_temp", "60.17,24.94", "--label", "Helsinki", "--from", "1990", "--scan")

    assert isinstance(inp, AnalyzeTrendInput)
    assert (inp.place.lat, inp.place.lon, inp.place.name) == (60.17, 24.94, "Helsinki")
    assert (inp.from_, inp.to, inp.season, inp.scan) == (1990, None, "annual", True)


def test_several_places_build_a_compare_input_with_labels_in_order() -> None:
    inp = parse("air_temp", "--label", "Helsinki", "--", "60.17,24.94", "-1.29,36.82")

    assert isinstance(inp, ComparePlacesInput)
    assert [place.name for place in inp.places] == ["Helsinki", None]


def test_negative_latitude_is_read_after_a_double_dash() -> None:
    inp = parse("air_temp", "--season", "DJF", "--", "-33.92,18.42")

    assert isinstance(inp, AnalyzeTrendInput)
    assert (inp.place.lat, inp.place.lon, inp.season) == (-33.92, 18.42, "DJF")


@pytest.mark.parametrize(
    "argv",
    [
        ["air_temp", "60.17"],
        ["air_temp", "60.17,24.94", "--season", "winter"],
        ["air_temp", "60.17,24.94", "--label", "A", "--label", "B"],
        ["air_temp", "95,24.94"],
        ["air_temp", "1,1", "2,2", "3,3", "4,4", "5,5"],
    ],
)
def test_arguments_that_do_not_form_a_case_exit_with_usage_error(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(argv)

    assert raised.value.code == 2


@pytest.mark.anyio
async def test_output_holds_verdicts_summary_numbers_link_and_steps() -> None:
    inp = parse("precipitation", "--label", "Helsinki", "--", "60.17,24.94", "-1.29,36.82")
    ctx = ToolContext(FakeSource(RISING), LAST_COMPLETE_YEAR, "https://trend.example")

    investigation = await run_case(inp, ctx)
    text = format_investigation(investigation)

    for result in investigation.results:
        assert result.verdict.sentence in text
    assert f"Summary: {investigation.summary}" in text
    assert "Sen's slope:       +0.50 mm/day per decade" in text
    assert "Caution: Rainfall trends from this model are less reliable" in text
    assert "Source: NASA POWER (MERRA-2), API v2.10.0, accessed 2026-11-13" in text
    assert f"Link: {investigation.app_url}" in text
    assert f"  1. {investigation.steps[0]}" in text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("variable", "expected"),
    [
        ("air_temp", "Helsinki: grid point 60.0, 25.0, cell 0.5° by 0.625°"),
        ("sunlight", "Helsinki: 1° by 1° cell centred on 60.5, 24.5"),
    ],
)
async def test_output_names_the_cell_of_the_variables_own_grid(
    variable: str, expected: str
) -> None:
    inp = parse(variable, "60.17,24.94", "--label", "Helsinki")

    investigation = await run_case(inp, ToolContext(FakeSource(RISING), LAST_COMPLETE_YEAR))

    assert format_investigation(investigation).splitlines()[2] == expected
