import pytest

from app.adapters.case_query import parse_case_query, parse_map_query, parse_query_string
from app.errors import BadPlaceError, BadRequestError
from app.models import AnalyzeTrendInput, ComparePlacesInput


def parse(text: str) -> AnalyzeTrendInput | ComparePlacesInput:
    return parse_case_query(parse_query_string(text))


def test_spec_example_gives_one_place_input() -> None:
    inp = parse("v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual")
    assert isinstance(inp, AnalyzeTrendInput)
    assert inp.variable == "air_temp"
    assert (inp.place.lat, inp.place.lon, inp.place.name) == (60.17, 24.94, "Helsinki")
    assert (inp.from_, inp.to, inp.season, inp.scan) == (1981, 2025, "annual", False)


def test_leading_question_mark_is_ignored() -> None:
    assert isinstance(parse("?v=air_temp&p=1,2"), AnalyzeTrendInput)


def test_two_places_give_a_comparison_with_labels_in_order() -> None:
    inp = parse("v=air_temp&p=1,2&p=3,4&label=A&label=")
    assert isinstance(inp, ComparePlacesInput)
    assert [(p.lat, p.lon, p.name) for p in inp.places] == [(1, 2, "A"), (3, 4, None)]


def test_period_and_season_default_when_absent() -> None:
    inp = parse("v=air_temp&p=1,2")
    assert (inp.from_, inp.to, inp.season) == (None, None, "annual")


def test_scan_one_turns_the_scan_on() -> None:
    assert parse("v=air_temp&p=1,2&scan=1").scan is True


@pytest.mark.parametrize(
    "text",
    [
        "p=1,2",
        "v=air_temp&v=precipitation&p=1,2",
        "v=air_temp&p=1,2&s=winter",
        "v=air_temp&p=1,2&from=nineteen",
        "v=air_temp&p=1,2&scan=yes",
        "v=air_temp&p=1,2&p=3,4&label=A",
        "v=air_temp&p=1,2&label=" + "x" * 41,
    ],
)
def test_invalid_parameters_are_bad_requests(text: str) -> None:
    with pytest.raises(BadRequestError):
        parse(text)


@pytest.mark.parametrize(
    "text",
    [
        "v=air_temp",
        "v=air_temp&p=91,0",
        "v=air_temp&p=0,181",
        "v=air_temp&p=1",
        "v=air_temp&p=north,east",
        "v=air_temp&p=nan,0",
        "v=air_temp&p=1,1&p=2,2&p=3,3&p=4,4&p=5,5",
    ],
)
def test_bad_places_are_bad_place_errors(text: str) -> None:
    with pytest.raises(BadPlaceError):
        parse(text)


def test_map_query_gives_a_box() -> None:
    inp = parse_map_query(parse_query_string("v=air_temp&box=55,20,65,30&from=1990&s=JJA"))
    assert (inp.box.south, inp.box.west, inp.box.north, inp.box.east) == (55, 20, 65, 30)
    assert (inp.from_, inp.season) == (1990, "JJA")


@pytest.mark.parametrize("box", ["55,20,65", "55,20,65,x", "95,20,65,30"])
def test_malformed_box_is_a_bad_place(box: str) -> None:
    with pytest.raises(BadPlaceError):
        parse_map_query(parse_query_string(f"v=air_temp&box={box}"))
