from collections import defaultdict

from app.catalogue import CatalogueEntry, GridAlignment, GridSize, load_catalogue, to_summary
from app.models import VariableSummary
from app.sources.power import CODES_ON_ONE_DEGREE_GRID, MAX_CODES_PER_CALL
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


def test_each_grid_s_codes_fit_in_one_point_call() -> None:
    # Spec 6: one point call fetches every code on a variable's grid, and POWER takes 20 at most.
    for grid in {entry.grid for entry in load_catalogue()}:
        codes = [entry.code for entry in load_catalogue() if entry.grid == grid]
        assert len(codes) <= MAX_CODES_PER_CALL


def test_haze_is_on_the_one_degree_grid_from_2001_and_handled_as_such_by_the_source() -> None:
    haze = next(entry for entry in load_catalogue() if entry.id == "haze")

    assert haze.grid == ONE_DEGREE_GRID
    assert haze.record_start == 2001
    assert haze.code in CODES_ON_ONE_DEGREE_GRID


def test_every_one_degree_code_of_the_catalogue_is_known_to_the_source() -> None:
    one_degree = {entry.code for entry in load_catalogue() if entry.grid == ONE_DEGREE_GRID}

    assert one_degree == CODES_ON_ONE_DEGREE_GRID


def test_strongest_wind_says_it_is_not_a_count_of_storms() -> None:
    wind = next(entry for entry in load_catalogue() if entry.id == "max_wind_speed")

    assert "highest hourly wind speed" in wind.definition
    assert "not a count of storms" in wind.definition


def test_haze_says_which_product_it_is_and_that_it_is_not_giovanni_modis() -> None:
    haze = next(entry for entry in load_catalogue() if entry.id == "haze")

    assert "CERES SYN1deg" in haze.definition
    assert "not from the MODIS Aqua product shown in Giovanni" in haze.definition
    assert "CERES SYN1deg" in haze.source


def test_model_snow_water_vapour_and_wind_carry_the_standing_caution() -> None:
    noted = {entry.id for entry in load_catalogue() if entry.trend_note}

    assert {"snow_depth", "snowfall", "snow_cover", "water_vapour", "max_wind_speed"} <= noted


def test_surface_temperature_says_what_it_means_over_the_sea() -> None:
    surface = next(entry for entry in load_catalogue() if entry.id == "surface_temp")

    assert "sea-surface temperature" in surface.definition


def test_sea_ice_warns_that_its_record_steps_down_in_the_mid_2000s() -> None:
    # Spec 6, "Catalogue additions": coastal sea-ice cells show an artificial step around
    # 2005 to 2007, so every sea-ice case carries this note as its caution.
    sea_ice = next(entry for entry in load_catalogue() if entry.id == "sea_ice")

    assert sea_ice.trend_note is not None
    assert "2005 to 2007" in sea_ice.trend_note
