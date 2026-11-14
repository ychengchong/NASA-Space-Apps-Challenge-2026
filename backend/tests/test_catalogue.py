from collections import defaultdict

from app.catalogue import CatalogueEntry, GridAlignment, GridSize, load_catalogue, to_summary
from app.models import VariableSummary
from app.tools.places import GRID_LAT_STEP, GRID_LON_STEP, load_places

# Spec 6, "A catalogue entry": every region type that places carry is suggested this many
# variables, at least and at most.
MIN_VARIABLES_PER_REGION_TYPE = 2
MAX_VARIABLES_PER_REGION_TYPE = 4
SOIL_WETNESS_IDS = frozenset({"surface_soil_wetness", "root_zone_soil_wetness"})
# Spec 6, "Places and grid cells": the two grids POWER serves the catalogue's variables on.
MERRA2_GRID = GridSize(
    height=GRID_LAT_STEP, width=GRID_LON_STEP, alignment=GridAlignment.CENTRED_ON_MULTIPLES
)
ONE_DEGREE_GRID = GridSize(height=1.0, width=1.0, alignment=GridAlignment.BOUNDED_BY_MULTIPLES)


def make_entry(**overrides: object) -> CatalogueEntry:
    fields: dict[str, object] = {
        "id": "precipitation",
        "code": "PRECTOTCORR",
        "name": "Precipitation",
        "definition": "How much rain and snow falls.",
        "keywords": ("rain",),
        "units": "mm/day",
        "rate_units": "mm/day",
        "decimals": 2,
        "record_start": 1981,
        "grid": {"height": 0.5, "width": 0.625, "alignment": "centred_on_multiples"},
        "theme": "water",
        "related": (),
        "source": "NASA POWER (MERRA-2)",
    }
    return CatalogueEntry.model_validate({**fields, **overrides})


def place_region_types() -> set[str]:
    return {record.region_type for record in load_places() if record.region_type}


def variables_by_region_type() -> dict[str, list[str]]:
    """The catalogue ids suggested for each region type, in catalogue order."""
    suggested: dict[str, list[str]] = defaultdict(list)
    for entry in load_catalogue():
        for region_type in entry.region_types:
            suggested[region_type].append(entry.id)
    return suggested


def test_every_region_type_of_a_place_is_suggested_two_to_four_variables() -> None:
    suggested = variables_by_region_type()

    counts = {region_type: len(suggested[region_type]) for region_type in place_region_types()}

    assert all(
        MIN_VARIABLES_PER_REGION_TYPE <= count <= MAX_VARIABLES_PER_REGION_TYPE
        for count in counts.values()
    ), counts


def test_every_region_type_in_the_catalogue_is_one_that_places_carry() -> None:
    assert set(variables_by_region_type()) <= place_region_types()


def test_an_entry_names_each_region_type_once() -> None:
    assert all(
        len(set(entry.region_types)) == len(entry.region_types) for entry in load_catalogue()
    )


def test_soil_wetness_is_never_suggested_for_an_ice_sheet() -> None:
    assert not SOIL_WETNESS_IDS & set(variables_by_region_type()["ice sheet"])


def test_every_variable_is_on_the_merra2_grid_or_the_one_degree_grid() -> None:
    # resolve_place snaps a grid centred on multiples to MERRA-2 grid points, and the POWER
    # client looks up cached boxes by them, so no other grid of that kind may appear.
    assert {entry.grid for entry in load_catalogue()} == {MERRA2_GRID, ONE_DEGREE_GRID}


def test_summary_carries_the_entry_region_types_in_order() -> None:
    summary = to_summary(make_entry(region_types=("savanna", "desert")))

    assert summary.region_types == ["savanna", "desert"]


def test_entry_without_region_types_gives_an_empty_list_in_json() -> None:
    summary = to_summary(make_entry())

    assert summary.model_dump(mode="json")["region_types"] == []


def test_variable_summary_defaults_to_no_region_types() -> None:
    fields = to_summary(make_entry()).model_dump(exclude={"region_types"})

    assert VariableSummary.model_validate(fields).region_types == []
