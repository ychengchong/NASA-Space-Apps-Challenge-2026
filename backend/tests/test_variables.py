from collections.abc import Callable

import pytest

from app.catalogue import CatalogueEntry, GridAlignment, GridSize, load_catalogue
from app.models import SearchVariablesInput, VariableSummary
from app.tools import variables
from app.tools.variables import search_variables

TEMPERATURE_IDS = ["air_temp", "max_temp", "min_temp", "surface_temp"]

InstallCatalogue = Callable[..., None]


def search_ids(query: str | None = None, theme: str | None = None) -> list[str]:
    return [
        summary.id for summary in search_variables(SearchVariablesInput(query=query, theme=theme))
    ]


def make_entry(
    entry_id: str, name: str, definition: str, keywords: tuple[str, ...] = ()
) -> CatalogueEntry:
    return CatalogueEntry(
        id=entry_id,
        code=entry_id.upper(),
        name=name,
        definition=definition,
        keywords=keywords,
        units="°C",
        rate_units="°C",
        decimals=2,
        record_start=1981,
        grid=GridSize(height=0.5, width=0.625, alignment=GridAlignment.CENTRED_ON_MULTIPLES),
        theme="test",
        related=(),
        source="test",
    )


@pytest.fixture
def use_catalogue(monkeypatch: pytest.MonkeyPatch) -> InstallCatalogue:
    """Replace the catalogue that search_variables reads with the given entries."""

    def install(*entries: CatalogueEntry) -> None:
        monkeypatch.setattr(variables, "load_catalogue", lambda: entries)

    return install


@pytest.mark.parametrize("query", [None, "", "   "])
def test_empty_query_returns_every_entry_in_catalogue_order(query: str | None) -> None:
    assert search_ids(query) == [entry.id for entry in load_catalogue()]


def test_query_of_only_function_words_returns_every_entry() -> None:
    assert search_ids("Is it the?") == [entry.id for entry in load_catalogue()]


def test_question_matches_on_its_meaningful_words_only() -> None:
    ids = search_ids("Is my city getting warmer?")

    assert ids[0] == "air_temp"
    assert len(ids) < len(load_catalogue())


def test_temperature_question_ranks_air_temperature_first() -> None:
    assert search_ids("Is the temperature rising in Helsinki?")[0] == "air_temp"


@pytest.mark.parametrize(
    ("question", "variable_id"),
    [
        ("Is it raining more?", "precipitation"),
        ("Are heatwaves getting worse?", "max_temp"),
        ("Is it getting cooler?", "air_temp"),
        ("Is it getting sunnier?", "sunlight"),
    ],
)
def test_common_question_phrasings_find_their_variable(question: str, variable_id: str) -> None:
    assert search_ids(question)[:1] == [variable_id]


def test_query_matching_ignores_case() -> None:
    assert search_ids("RAIN")[0] == "precipitation"


def test_query_splits_words_on_punctuation() -> None:
    assert search_ids("root-zone?")[0] == "root_zone_soil_wetness"


def test_query_that_matches_nothing_returns_empty_list() -> None:
    assert search_ids("volcano") == []


def test_theme_keeps_only_entries_of_that_exact_theme() -> None:
    assert search_ids(theme="temperature") == TEMPERATURE_IDS
    assert search_ids(theme="Temperature") == []


def test_theme_and_query_combine() -> None:
    assert search_ids("humidity", theme="water") == ["relative_humidity", "specific_humidity"]
    assert search_ids("humidity", theme="temperature") == []


def test_results_are_variable_summaries_without_the_power_code() -> None:
    summary = search_variables(SearchVariablesInput(query="cloud"))[0]

    assert isinstance(summary, VariableSummary)
    assert "code" not in summary.model_dump()


def test_entry_matching_more_query_words_ranks_first(use_catalogue: InstallCatalogue) -> None:
    use_catalogue(
        make_entry("one", "Soil wetness", "How wet the soil is."),
        make_entry("two", "Root-zone soil wetness", "How wet the soil is near roots."),
    )

    assert search_ids("root soil") == ["two", "one"]


def test_keyword_match_ranks_before_name_match_before_definition_match(
    use_catalogue: InstallCatalogue,
) -> None:
    use_catalogue(
        make_entry("in_definition", "Alpha", "Measures frost on the ground."),
        make_entry("in_name", "Frost days", "Counts cold days."),
        make_entry("in_keywords", "Beta", "Counts cold nights.", keywords=("frost",)),
    )

    assert search_ids("frost") == ["in_keywords", "in_name", "in_definition"]


def test_equal_matches_keep_catalogue_order(use_catalogue: InstallCatalogue) -> None:
    use_catalogue(
        make_entry("first", "Gamma", "Rain."),
        make_entry("second", "Delta", "Rain."),
    )

    assert search_ids("rain") == ["first", "second"]


def test_definition_match_does_not_break_a_tie(use_catalogue: InstallCatalogue) -> None:
    use_catalogue(
        make_entry("first", "Frost", "Counts cold nights.", keywords=("frost",)),
        make_entry("second", "Frost", "Counts frost nights.", keywords=("frost",)),
    )

    assert search_ids("frost") == ["first", "second"]


def test_query_words_match_whole_words_only(use_catalogue: InstallCatalogue) -> None:
    use_catalogue(make_entry("warming", "Heat", "Air.", keywords=("warmer",)))

    assert search_ids("warm") == []


# The variables of the challenge video (spec 6, "Catalogue additions")


@pytest.mark.parametrize(
    ("query", "first"),
    [
        ("snow", "snow_depth"),
        ("sea ice", "sea_ice"),
        ("haze", "haze"),
        ("Is the air getting hazier?", "haze"),
        ("smoke", "haze"),
        ("pressure", "surface_pressure"),
        ("ocean", "surface_temp"),
        ("Is the ocean warming?", "surface_temp"),
        ("sea surface temperature", "surface_temp"),
        ("water vapour", "water_vapour"),
        ("strongest wind", "max_wind_speed"),
        ("snowfall", "snowfall"),
        ("snow cover", "snow_cover"),
        ("Is the sea level rising?", "surface_temp"),
    ],
)
def test_words_of_the_challenge_video_find_their_variable_first(query: str, first: str) -> None:
    assert search_ids(query)[0] == first
