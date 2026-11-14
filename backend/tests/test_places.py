import json
import math
import zipfile
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest

from app.catalogue import get_entry
from app.models import FindPlaceInput, PlaceCandidate, PlaceInput
from app.tools import places
from app.tools.places import (
    PLACES_PATH,
    PlaceRecord,
    find_place,
    format_coordinates,
    load_places,
    resolve_place,
    round_link_coordinate,
    snap_to_grid,
)
from scripts.build_places import (
    GEONAMES_COLUMNS,
    MEGACITY_POPULATION,
    MIN_CITY_POPULATION,
    REGIONS,
    build_places,
    region_record,
    to_json,
)

# Grid snapping (spec 6)


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (55.2, 20.4, (55.0, 20.625)),
        (60.17, 24.94, (60.0, 25.0)),
        (-33.87, 151.21, (-34.0, 151.25)),
        (-0.1, -0.1, (0.0, 0.0)),
    ],
)
def test_snap_to_grid_returns_nearest_merra2_grid_point(
    lat: float, lon: float, expected: tuple[float, float]
) -> None:
    assert snap_to_grid(lat, lon) == expected


def test_snap_to_grid_sends_a_halfway_point_north_and_east() -> None:
    assert snap_to_grid(55.25, 0.3125) == (55.5, 0.625)


@pytest.mark.parametrize("lon", [179.9, 180.0, -180.0, -179.8])
def test_snap_to_grid_wraps_longitude_into_minus_180_to_180(lon: float) -> None:
    assert snap_to_grid(0.0, lon) == (0.0, -180.0)


@pytest.mark.parametrize(("lat", "expected"), [(89.9, 90.0), (90.0, 90.0), (-89.9, -90.0)])
def test_snap_to_grid_keeps_latitude_within_the_poles(lat: float, expected: float) -> None:
    assert snap_to_grid(lat, 0.0)[0] == expected


# Coordinates as text and in links (spec 5 and 11)


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (60.0, 25.0, "60.0°N, 25.0°E"),
        (-34.0, -58.125, "34.0°S, 58.1°W"),
        (0.0, -180.0, "0.0°N, 180.0°W"),
        (-0.02, -0.04, "0.0°N, 0.0°E"),
    ],
)
def test_format_coordinates_uses_one_decimal_and_hemisphere_letters(
    lat: float, lon: float, expected: str
) -> None:
    assert format_coordinates(lat, lon) == expected


@pytest.mark.parametrize(
    ("x", "expected"), [(60.16952, 60.17), (24.93545, 24.94), (-1.28333, -1.28)]
)
def test_round_link_coordinate_keeps_two_decimals(x: float, expected: float) -> None:
    assert round_link_coordinate(x) == x


def test_round_link_coordinate_never_returns_negative_zero() -> None:
    assert math.copysign(1.0, round_link_coordinate(-0.0)) == 1.0


# resolve_place (spec 5, Place)


def test_resolve_place_keeps_given_name_and_requested_coordinates() -> None:
    place = resolve_place(PlaceInput(lat=60.17, lon=24.94, name="Helsinki"), get_entry("air_temp"))

    assert place.name == "Helsinki"
    assert (place.lat, place.lon) == (60.17, 24.94)
    assert place.cell.model_dump() == {"lat": 60.0, "lon": 25.0, "height": 0.5, "width": 0.625}


@pytest.mark.parametrize("name", [None, "", "   "])
def test_resolve_place_without_name_is_named_by_its_grid_point(name: str | None) -> None:
    place = resolve_place(PlaceInput(lat=60.17, lon=24.94, name=name), get_entry("air_temp"))

    assert place.name == "60.0°N, 25.0°E"


@pytest.mark.parametrize(
    ("lat", "lon"), [(60.17, 24.94), (59.76, 25.3), (60.0, 25.0), (-23.0, -45.0), (89.99, 0.0)]
)
def test_resolve_place_keeps_merra2_variables_at_the_nearest_grid_point(
    lat: float, lon: float
) -> None:
    place = resolve_place(PlaceInput(lat=lat, lon=lon), get_entry("air_temp"))

    assert (place.cell.lat, place.cell.lon) == snap_to_grid(lat, lon)
    assert (place.cell.height, place.cell.width) == (0.5, 0.625)


# Spec 6, "Limits we observed": POWER answers sunlight and cloud from the 1° cell, bounded by
# whole degrees, that holds the requested point. A point on a whole-degree line takes the cell
# north or east of it.
@pytest.mark.parametrize("variable", ["sunlight", "cloud_cover"])
@pytest.mark.parametrize(
    ("lat", "lon", "centre"),
    [
        (60.17, 24.94, (60.5, 24.5)),
        (59.76, 25.3, (59.5, 25.5)),
        (60.0, 25.0, (60.5, 25.5)),
        (-23.0, -45.0, (-22.5, -44.5)),
    ],
)
def test_resolve_place_reports_the_one_degree_cell_that_holds_the_place(
    variable: str, lat: float, lon: float, centre: tuple[float, float]
) -> None:
    place = resolve_place(PlaceInput(lat=lat, lon=lon), get_entry(variable))

    assert place.cell.model_dump() == {
        "lat": centre[0],
        "lon": centre[1],
        "height": 1.0,
        "width": 1.0,
    }


@pytest.mark.parametrize("lat", [89.99, 90.0])
def test_resolve_place_keeps_a_one_degree_cell_south_of_the_pole(lat: float) -> None:
    place = resolve_place(PlaceInput(lat=lat, lon=0.0), get_entry("sunlight"))

    assert place.cell.lat == 89.5


@pytest.mark.parametrize(
    ("lon", "expected"),
    [(180.0, -179.5), (-180.0, -179.5), (179.99, 179.5), (179.999, 179.5)],
)
def test_resolve_place_wraps_the_longitude_of_a_one_degree_cell(
    lon: float, expected: float
) -> None:
    place = resolve_place(PlaceInput(lat=0.0, lon=lon), get_entry("sunlight"))

    assert place.cell.lon == expected


def test_resolve_place_without_name_is_named_by_the_centre_of_its_one_degree_cell() -> None:
    place = resolve_place(PlaceInput(lat=60.17, lon=24.94), get_entry("cloud_cover"))

    assert place.name == "60.5°N, 24.5°E"


def test_resolve_place_finds_the_one_degree_cell_of_the_coordinates_in_the_link() -> None:
    # A link writes 59.996 as 60.0, which lies on the south edge of the cell from 60° to 61° N.
    place = resolve_place(PlaceInput(lat=59.996, lon=25.0), get_entry("sunlight"))

    assert (place.cell.lat, place.cell.lon) == (59.5, 25.5)


@pytest.mark.parametrize(
    ("requested", "in_link"),
    [((59.9386, 30.3141), (59.94, 30.31)), ((60.249, 25.0), (60.25, 25.0))],
)
def test_resolve_place_analyses_the_cell_of_the_coordinates_in_the_link(
    requested: tuple[float, float], in_link: tuple[float, float]
) -> None:
    entry = get_entry("air_temp")

    from_request = resolve_place(PlaceInput(lat=requested[0], lon=requested[1]), entry)
    from_link = resolve_place(
        PlaceInput(
            lat=round_link_coordinate(requested[0]), lon=round_link_coordinate(requested[1])
        ),
        entry,
    )

    assert (from_request.cell, from_request.name) == (from_link.cell, from_link.name)


def test_resolve_place_keeps_requested_coordinates_that_a_link_would_round() -> None:
    place = resolve_place(PlaceInput(lat=59.9386, lon=30.3141), get_entry("air_temp"))

    assert (place.lat, place.lon) == (59.9386, 30.3141)


# find_place (spec 5) on the bundled places.json


def find(query: str) -> list[PlaceCandidate]:
    return find_place(FindPlaceInput(query=query))


def population_of(candidate: PlaceCandidate) -> int:
    for record in load_places():
        if (record.name, record.lat, record.lon) == (candidate.name, candidate.lat, candidate.lon):
            return record.population
    raise AssertionError(f"{candidate.name} is not in places.json")


@pytest.mark.parametrize("query", ["São Paulo", "sao paulo", "SAO PAULO", "  são   PAULO "])
def test_find_place_ignores_case_accents_and_extra_spaces(query: str) -> None:
    first = find(query)[0]

    assert (first.name, first.country, first.kind) == ("São Paulo", "Brazil", "city")


def test_find_place_matches_alternative_names() -> None:
    assert find("Lodz")[0].name == "Łódź"


def test_find_place_returns_at_most_five_matches() -> None:
    assert len(find("san")) == 5


@pytest.mark.parametrize(
    ("query", "name", "country"),
    [
        ("Paris", "Paris", "France"),
        ("Male", "Male", "Maldives"),
        ("Malé", "Male", "Maldives"),
        ("york", "York", "United Kingdom"),
        ("Sahara", "Sahara", None),
    ],
)
def test_find_place_ranks_an_exact_name_match_first(
    query: str, name: str, country: str | None
) -> None:
    first = find(query)[0]

    assert (first.name, first.country) == (name, country)


def test_find_place_ranks_exact_then_starting_then_containing_matches() -> None:
    names = [candidate.name for candidate in find("Male")]

    assert names == ["Male", "Malegaon", "Māler Kotla", "Tamale", "Trincomalee"]


def test_find_place_ranks_most_populous_first_within_a_group() -> None:
    populations = [population_of(candidate) for candidate in find("santa")]

    assert populations == sorted(populations, reverse=True)


def test_find_place_ranks_regions_after_cities_within_a_group() -> None:
    found = [(candidate.name, candidate.kind) for candidate in find("mississ")]

    assert found == [("Mississauga", "city"), ("Mississippi River Delta", "region")]


@pytest.fixture
def use_places(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    """Replaces the bundled places with the records given, for one test."""

    def install(*records: PlaceRecord) -> None:
        monkeypatch.setattr(places, "load_places", lambda: records)
        places._search_index.cache_clear()

    yield install
    places._search_index.cache_clear()


def test_find_place_ranks_an_exact_alternative_name_as_an_exact_match(
    use_places: Callable[..., None],
) -> None:
    use_places(
        PlaceRecord(name="Springfield Heights", lat=0.0, lon=0.0, population=900_000, kind="city"),
        PlaceRecord(
            name="Old Town",
            alt_names=("Springfield",),
            lat=1.0,
            lon=1.0,
            population=50_000,
            kind="city",
        ),
    )

    assert [candidate.name for candidate in find("springfield")] == [
        "Old Town",
        "Springfield Heights",
    ]


def test_find_place_returns_regions_with_their_type() -> None:
    regions = [candidate for candidate in find("Gobi") if candidate.kind == "region"]

    assert [(region.name, region.region_type) for region in regions] == [("Gobi Desert", "desert")]


def test_find_place_finds_svalbard_by_the_name_of_its_town_longyearbyen() -> None:
    found = [
        (candidate.name, candidate.country, candidate.kind, candidate.region_type)
        for candidate in find("Longyearbyen")
    ]

    assert found == [("Svalbard", "Norway", "region", "tundra")]


def test_svalbard_sits_at_the_headline_examples_point_in_longyearbyen() -> None:
    (svalbard,) = find("Svalbard")

    assert (svalbard.lat, svalbard.lon) == (78.22, 15.65)


def test_find_place_tags_cities_of_ten_million_as_megacities() -> None:
    assert find("Shanghai")[0].region_type == "megacity"


def test_find_place_returns_only_the_spec_fields() -> None:
    fields = set(find("Helsinki")[0].model_dump())

    assert fields == {"name", "country", "lat", "lon", "kind", "region_type"}


@pytest.mark.parametrize("query", ["Qwxyzzyq", "   "])
def test_find_place_without_a_match_returns_empty_list(query: str) -> None:
    assert find(query) == []


# The bundled places.json and the script that builds it


def test_bundled_cities_have_at_least_the_minimum_population() -> None:
    cities = [record for record in load_places() if record.kind == "city"]

    assert cities
    assert all(record.population >= MIN_CITY_POPULATION for record in cities)
    assert all(
        (record.region_type == "megacity") == (record.population >= MEGACITY_POPULATION)
        for record in cities
    )


def test_bundled_regions_are_the_hand_picked_regions() -> None:
    regions = [record for record in load_places() if record.kind == "region"]

    assert [record.name for record in regions] == [region["name"] for region in REGIONS]
    assert all(record.hand_picked and record.region_type for record in regions)


def test_bundled_regions_are_the_records_the_script_writes() -> None:
    raw = json.loads(PLACES_PATH.read_text(encoding="utf-8"))
    regions = [place for place in raw["places"] if place["kind"] == "region"]

    assert regions == [region_record(region) for region in REGIONS]


def geonames_row(name: str, ascii_name: str, cc: str, population: int, code: str = "PPL") -> str:
    row = [""] * GEONAMES_COLUMNS
    row[0], row[1], row[2] = "1", name, ascii_name
    row[4], row[5], row[6], row[7], row[8] = "51.770581", "19.473951", "P", code, cc
    row[14] = str(population)
    return "\t".join(row)


@pytest.fixture
def geonames_files(tmp_path: Path) -> tuple[Path, Path]:
    rows = [
        geonames_row("Łódź", "Lodz", "PL", 639_890),
        geonames_row("Bigtown", "Bigtown", "PL", 12_000_000),
        geonames_row("Smalltown", "Smalltown", "PL", 99_999),
        geonames_row("Oldtown", "Oldtown", "PL", 200_000, code="PPLH"),
        geonames_row("Nowhere", "Nowhere", "ZZ", 150_000),
    ]
    cities_zip = tmp_path / "cities15000.zip"
    with zipfile.ZipFile(cities_zip, "w") as archive:
        archive.writestr("cities15000.txt", "\n".join(rows) + "\n")
    country_info = tmp_path / "countryInfo.txt"
    country_info.write_text("#ISO\tISO3\tISO-Numeric\tfips\tCountry\nPL\tPOL\t616\tPL\tPoland\n")
    return cities_zip, country_info


def test_build_places_keeps_large_current_cities_most_populous_first(
    geonames_files: tuple[Path, Path],
) -> None:
    document = build_places(*geonames_files, downloaded=date(2026, 11, 13))
    cities = [place for place in document["places"] if place["kind"] == "city"]

    assert cities == [
        {
            "name": "Bigtown",
            "country": "Poland",
            "lat": 51.7706,
            "lon": 19.474,
            "population": 12_000_000,
            "kind": "city",
            "region_type": "megacity",
        },
        {
            "name": "Łódź",
            "alt_names": ["Lodz"],
            "country": "Poland",
            "lat": 51.7706,
            "lon": 19.474,
            "population": 639_890,
            "kind": "city",
        },
        {"name": "Nowhere", "lat": 51.7706, "lon": 19.474, "population": 150_000, "kind": "city"},
    ]


def test_build_places_adds_hand_picked_regions_and_attribution(
    geonames_files: tuple[Path, Path],
) -> None:
    document = build_places(*geonames_files, downloaded=date(2026, 11, 13))
    regions = [place for place in document["places"] if place["kind"] == "region"]

    assert len(regions) == len(REGIONS)
    assert all(region["hand_picked"] for region in regions)
    assert all(part in document["attribution"] for part in ("GeoNames", "CC BY 4.0", "2026-11-13"))


def test_build_places_output_is_valid_json(geonames_files: tuple[Path, Path]) -> None:
    document = build_places(*geonames_files, downloaded=date(2026, 11, 13))

    assert json.loads(to_json(document)) == document
