from typing import get_args

import pytest

from app.catalogue import CatalogueEntry, GridAlignment, GridSize
from app.models import Caution, Cell, Direction, Place, PlaceResult, Trend, Verdict, VerdictKind
from app.verdict import (
    build_verdict,
    caution_text,
    compare_places_summary,
    format_rate,
    format_signed_rate,
)

SOURCE_CHANGE_TEXT = (
    "The data source for this variable changes in 2001, which can create an artificial step."
)
SHORT_RECORD_TEXT = "This record is short. Trends in short records often fade as more years arrive."
AUTOCORRELATED_TEXT = (
    "Each year here resembles the one before. "
    "The test allows for that, which makes it harder to pass."
)
METHODS_DISAGREE_TEXT = "Two standard methods disagree about this trend."
BORDERLINE_TEXT = "This result is close to the threshold for significance."
RAIN_NOTE = "Rainfall trends from this model are less reliable than temperature trends."


def make_entry(**overrides: object) -> CatalogueEntry:
    fields: dict[str, object] = {
        "id": "air_temp",
        "code": "T2M",
        "name": "Air temperature",
        "definition": "How warm the air is two metres above the ground.",
        "keywords": ("temperature",),
        "units": "°C",
        "rate_units": "°C",
        "decimals": 2,
        "record_start": 1981,
        "grid": GridSize(height=0.5, width=0.625, alignment=GridAlignment.CENTRED_ON_MULTIPLES),
        "theme": "temperature",
        "related": (),
        "source": "NASA POWER (MERRA-2)",
    }
    return CatalogueEntry.model_validate({**fields, **overrides})


def make_trend(**overrides: object) -> Trend:
    """A clear, significant warming trend that triggers no caution unless overridden."""
    fields: dict[str, object] = {
        "n": 45,
        "first_year": 1981,
        "last_year": 2025,
        "sen_slope": 0.25,
        "sen_ci95": (0.18, 0.32),
        "line": (14.0, 15.1),
        "total_change": 1.1,
        "mk_p": 0.001,
        "lag1": 0.1,
        "variance_factor": 1.22,
        "ols_slope": 0.26,
        "ols_p": 0.001,
    }
    return Trend.model_validate({**fields, **overrides})


def make_result(name: str, kind: VerdictKind, direction: Direction | None) -> PlaceResult:
    return PlaceResult(
        place=Place(
            name=name, lat=0.0, lon=0.0, cell=Cell(lat=0.0, lon=0.0, height=0.5, width=0.625)
        ),
        series=[],
        trend=None,
        verdict=Verdict(kind=kind, direction=direction, sentence="", cautions=[]),
    )


def cautions_for(entry: CatalogueEntry, trend: Trend) -> list[Caution]:
    return build_verdict(entry, "Helsinki", trend.n, trend).cautions


# format_rate and format_signed_rate


def test_rate_is_rounded_to_the_variable_decimals() -> None:
    assert format_rate(0.2449, 2) == "0.24"
    assert format_rate(0.36, 1) == "0.4"


def test_rate_keeps_trailing_zeros() -> None:
    assert format_rate(0.3, 2) == "0.30"


def test_rate_shows_the_size_without_a_sign() -> None:
    assert format_rate(-0.236, 2) == "0.24"


def test_rate_that_rounds_to_zero_shows_one_more_digit() -> None:
    assert format_rate(0.004, 2) == "0.004"
    assert format_rate(-0.0004, 3) == "0.0004"


def test_rate_shows_only_one_extra_digit() -> None:
    assert format_rate(0.0004, 2) == "0.000"


def test_rate_rounds_an_exact_tie_to_the_even_digit_like_the_frontend() -> None:
    assert format_rate(0.125, 2) == "0.12"
    assert format_rate(0.375, 2) == "0.38"


def test_rate_rounds_an_exact_tie_to_a_whole_number_to_the_even_number() -> None:
    assert format_rate(2.5, 0) == "2"
    assert format_rate(3.5, 0) == "4"


def test_rate_with_zero_decimals_has_no_point() -> None:
    assert format_rate(2.7, 0) == "3"


def test_signed_rate_has_a_plus_for_a_rise() -> None:
    assert format_signed_rate(0.1234, 2) == "+0.12"


def test_signed_rate_rounds_the_size_of_a_fall() -> None:
    assert format_signed_rate(-0.236, 2) == "-0.24"


def test_signed_rate_rounds_a_negative_exact_tie_to_the_even_digit() -> None:
    assert format_signed_rate(-0.125, 2) == "-0.12"


def test_signed_rate_keeps_the_sign_when_an_extra_digit_is_shown() -> None:
    assert format_signed_rate(-0.004, 2) == "-0.004"


def test_signed_rate_of_exactly_zero_has_no_sign() -> None:
    assert format_signed_rate(0.0, 2) == "0.000"


# build_verdict: kinds and sentences


def test_no_yearly_values_gives_no_data() -> None:
    verdict = build_verdict(make_entry(), "Helsinki", 0, None)

    assert verdict.kind == "no_data"
    assert verdict.direction is None
    assert verdict.sentence == "There is no air temperature data for this location."


def test_no_data_carries_the_variable_note() -> None:
    verdict = build_verdict(make_entry(trend_note=RAIN_NOTE), "Helsinki", 0, None)

    assert verdict.cautions == ["variable_note"]


def test_no_data_without_a_trend_note_has_no_cautions() -> None:
    verdict = build_verdict(make_entry(), "Helsinki", 0, None)

    assert verdict.cautions == []


def test_fewer_than_ten_years_gives_too_few_years() -> None:
    verdict = build_verdict(make_entry(), "Helsinki", 9, None)

    assert verdict.kind == "too_few_years"
    assert verdict.direction is None
    assert verdict.sentence == (
        "There are only 9 complete years of air temperature data here. "
        "That is too few to test for a trend."
    )
    assert verdict.cautions == []


def test_one_complete_year_reads_in_the_singular() -> None:
    verdict = build_verdict(make_entry(), "Helsinki", 1, None)

    assert verdict.sentence == (
        "There is only 1 complete year of air temperature data here. "
        "That is too few to test for a trend."
    )


def test_too_few_years_carries_the_variable_note() -> None:
    verdict = build_verdict(make_entry(trend_note=RAIN_NOTE), "Helsinki", 5, None)

    assert verdict.cautions == ["variable_note"]


def test_variable_lowercases_only_its_first_letter_inside_a_sentence() -> None:
    entry = make_entry(name="Wind speed at 10 m")

    verdict = build_verdict(entry, "Helsinki", 0, None)

    assert verdict.sentence == "There is no wind speed at 10 m data for this location."


def test_significant_rise_reads_risen() -> None:
    verdict = build_verdict(make_entry(), "Helsinki", 45, make_trend())

    assert verdict.kind == "significant"
    assert verdict.direction == "rising"
    assert verdict.sentence == (
        "Air temperature in Helsinki has risen by about 0.25 °C per decade "
        "from 1981 to 2025. This trend is statistically significant."
    )


def test_significant_fall_reads_fallen_with_the_size_of_the_rate() -> None:
    trend = make_trend(sen_slope=-0.25)

    verdict = build_verdict(make_entry(), "Helsinki", 45, trend)

    assert verdict.kind == "significant"
    assert verdict.direction == "falling"
    assert verdict.sentence == (
        "Air temperature in Helsinki has fallen by about 0.25 °C per decade "
        "from 1981 to 2025. This trend is statistically significant."
    )


def test_not_significant_rise_shows_the_signed_rate() -> None:
    trend = make_trend(sen_slope=0.1234, mk_p=0.4, ols_p=0.4)

    verdict = build_verdict(make_entry(), "Helsinki", 45, trend)

    assert verdict.kind == "not_significant"
    assert verdict.direction == "rising"
    assert verdict.sentence == (
        "Air temperature in Helsinki changed by about +0.12 °C per decade from 1981 to 2025. "
        "Year-to-year variation alone could produce a change this size, "
        "so the trend is not statistically significant."
    )


def test_not_significant_fall_shows_a_minus_sign() -> None:
    trend = make_trend(sen_slope=-0.1234, mk_p=0.4, ols_p=0.4)

    verdict = build_verdict(make_entry(), "Helsinki", 45, trend)

    assert verdict.direction == "falling"
    assert "changed by about -0.12 °C per decade" in verdict.sentence


def test_p_of_exactly_the_significance_level_is_not_significant() -> None:
    trend = make_trend(mk_p=0.05, ols_p=0.05)

    verdict = build_verdict(make_entry(), "Helsinki", 45, trend)

    assert verdict.kind == "not_significant"
    assert verdict.direction == "rising"


def test_zero_slope_has_no_direction_and_its_own_sentence() -> None:
    trend = make_trend(sen_slope=0.0, mk_p=0.6, ols_p=0.6)

    verdict = build_verdict(make_entry(), "Helsinki", 45, trend)

    assert verdict.kind == "not_significant"
    assert verdict.direction is None
    assert verdict.sentence == (
        "Air temperature in Helsinki shows no upward or downward trend from 1981 to 2025."
    )


def test_zero_slope_is_not_significant_even_with_a_small_p() -> None:
    trend = make_trend(sen_slope=0.0, mk_p=0.01)

    verdict = build_verdict(make_entry(), "Helsinki", 45, trend)

    assert verdict.kind == "not_significant"
    assert verdict.direction is None


def test_sentence_uses_the_years_actually_used() -> None:
    trend = make_trend(n=36, first_year=1984, last_year=2021)

    verdict = build_verdict(make_entry(), "Helsinki", 36, trend)

    assert "from 1984 to 2021." in verdict.sentence


def test_sentence_shows_the_place_name_as_given() -> None:
    verdict = build_verdict(make_entry(), "60.0°N, 25.0°E", 45, make_trend())

    assert verdict.sentence.startswith("Air temperature in 60.0°N, 25.0°E has risen")


def test_rate_units_follow_the_rate() -> None:
    entry = make_entry(rate_units="percentage points", decimals=1)
    trend = make_trend(sen_slope=0.43)

    verdict = build_verdict(entry, "Helsinki", 45, trend)

    assert "by about 0.4 percentage points per decade" in verdict.sentence


def test_empty_rate_units_leave_no_double_space() -> None:
    entry = make_entry(name="Surface soil wetness", rate_units="", decimals=3)
    trend = make_trend(sen_slope=0.0123)

    verdict = build_verdict(entry, "Kano", 45, trend)

    assert verdict.sentence == (
        "Surface soil wetness in Kano has risen by about 0.012 per decade "
        "from 1981 to 2025. This trend is statistically significant."
    )


def test_empty_rate_units_with_a_signed_rate() -> None:
    entry = make_entry(name="Surface soil wetness", rate_units="", decimals=3)
    trend = make_trend(sen_slope=-0.0123, mk_p=0.4, ols_p=0.4)

    verdict = build_verdict(entry, "Kano", 45, trend)

    assert "changed by about -0.012 per decade from" in verdict.sentence


def test_sentence_uses_the_extra_digit_for_a_tiny_rate() -> None:
    trend = make_trend(sen_slope=0.004, mk_p=0.4, ols_p=0.4)

    verdict = build_verdict(make_entry(), "Helsinki", 45, trend)

    assert "changed by about +0.004 °C per decade" in verdict.sentence


def test_testable_record_without_a_trend_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_verdict(make_entry(), "Helsinki", 10, None)


# build_verdict: cautions


def test_clean_trend_has_no_cautions() -> None:
    assert cautions_for(make_entry(), make_trend()) == []


def test_trend_crossing_a_source_change_gets_source_change() -> None:
    entry = make_entry(source_changes=(2001,))
    trend = make_trend(n=42, first_year=1984)

    assert cautions_for(entry, trend) == ["source_change"]


def test_trend_ending_in_the_change_year_gets_source_change() -> None:
    entry = make_entry(source_changes=(2001,))
    trend = make_trend(n=18, first_year=1984, last_year=2001)

    assert "source_change" in cautions_for(entry, trend)


def test_trend_starting_in_the_change_year_has_no_source_change() -> None:
    entry = make_entry(source_changes=(2001,))
    trend = make_trend(n=25, first_year=2001)

    assert "source_change" not in cautions_for(entry, trend)


def test_trend_ending_before_the_change_year_has_no_source_change() -> None:
    entry = make_entry(source_changes=(2001,))
    trend = make_trend(n=17, first_year=1984, last_year=2000)

    assert "source_change" not in cautions_for(entry, trend)


def test_variable_with_a_trend_note_gets_variable_note() -> None:
    entry = make_entry(trend_note=RAIN_NOTE)

    assert cautions_for(entry, make_trend()) == ["variable_note"]


def test_fewer_than_twenty_years_gets_short_record() -> None:
    assert cautions_for(make_entry(), make_trend(n=19)) == ["short_record"]


def test_twenty_years_is_not_short() -> None:
    assert cautions_for(make_entry(), make_trend(n=20)) == []


def test_lag1_of_point_three_gets_autocorrelated() -> None:
    assert cautions_for(make_entry(), make_trend(lag1=0.3)) == ["autocorrelated"]


def test_lag1_below_point_three_is_not_autocorrelated() -> None:
    assert cautions_for(make_entry(), make_trend(lag1=0.29)) == []


def test_only_mann_kendall_significant_gets_methods_disagree() -> None:
    trend = make_trend(mk_p=0.01, ols_p=0.2)

    assert cautions_for(make_entry(), trend) == ["methods_disagree"]


def test_only_t_test_significant_gets_methods_disagree() -> None:
    trend = make_trend(mk_p=0.2, ols_p=0.01)

    assert cautions_for(make_entry(), trend) == ["methods_disagree"]


def test_both_methods_not_significant_agree() -> None:
    trend = make_trend(mk_p=0.2, ols_p=0.3)

    assert cautions_for(make_entry(), trend) == []


def test_p_at_either_end_of_the_borderline_range_gets_borderline() -> None:
    low = make_trend(mk_p=0.025, ols_p=0.025)
    high = make_trend(mk_p=0.10, ols_p=0.10)

    assert cautions_for(make_entry(), low) == ["borderline"]
    assert cautions_for(make_entry(), high) == ["borderline"]


def test_p_outside_the_borderline_range_is_not_borderline() -> None:
    below = make_trend(mk_p=0.0249, ols_p=0.0249)
    above = make_trend(mk_p=0.1001, ols_p=0.1001)

    assert cautions_for(make_entry(), below) == []
    assert cautions_for(make_entry(), above) == []


def test_cautions_are_listed_most_important_first() -> None:
    entry = make_entry(source_changes=(2001,), trend_note=RAIN_NOTE)
    trend = make_trend(n=15, first_year=1990, last_year=2010, lag1=0.5, mk_p=0.06, ols_p=0.01)

    assert cautions_for(entry, trend) == [
        "source_change",
        "variable_note",
        "short_record",
        "autocorrelated",
        "methods_disagree",
        "borderline",
    ]


# caution_text


def test_source_change_text_names_the_year_crossed() -> None:
    entry = make_entry(source_changes=(2001, 2015))
    trend = make_trend(n=27, first_year=1984, last_year=2010)

    assert caution_text("source_change", entry, trend) == SOURCE_CHANGE_TEXT


def test_source_change_text_needs_a_trend() -> None:
    with pytest.raises(ValueError):
        caution_text("source_change", make_entry(source_changes=(2001,)))


def test_variable_note_text_is_the_note_itself() -> None:
    entry = make_entry(trend_note=RAIN_NOTE)

    assert caution_text("variable_note", entry) == RAIN_NOTE


def test_variable_note_text_needs_a_note() -> None:
    with pytest.raises(ValueError):
        caution_text("variable_note", make_entry())


def test_fixed_caution_texts_match_the_spec() -> None:
    entry = make_entry()

    assert caution_text("short_record", entry) == SHORT_RECORD_TEXT
    assert caution_text("autocorrelated", entry) == AUTOCORRELATED_TEXT
    assert caution_text("methods_disagree", entry) == METHODS_DISAGREE_TEXT
    assert caution_text("borderline", entry) == BORDERLINE_TEXT


def test_every_caution_has_a_text() -> None:
    entry = make_entry(source_changes=(2001,), trend_note=RAIN_NOTE)
    trend = make_trend(first_year=1984)

    for caution in get_args(Caution):
        assert caution_text(caution, entry, trend)


# compare_places_summary


def test_significant_rise_and_fall_are_opposite() -> None:
    results = [
        make_result("Helsinki", "significant", "rising"),
        make_result("Nairobi", "significant", "falling"),
    ]

    contrast, summary = compare_places_summary(make_entry(), results)

    assert contrast == "opposite_directions"
    assert summary == (
        "Air temperature is rising significantly in Helsinki "
        "and falling significantly in Nairobi over the same years."
    )


def test_opposite_summary_joins_several_place_names() -> None:
    results = [
        make_result("Helsinki", "significant", "rising"),
        make_result("Oslo", "significant", "rising"),
        make_result("Riga", "significant", "rising"),
        make_result("Nairobi", "significant", "falling"),
    ]

    _, summary = compare_places_summary(make_entry(), results)

    assert summary == (
        "Air temperature is rising significantly in Helsinki, Oslo and Riga "
        "and falling significantly in Nairobi over the same years."
    )


def test_opposite_summary_joins_two_place_names_with_and() -> None:
    results = [
        make_result("Helsinki", "significant", "rising"),
        make_result("Nairobi", "significant", "falling"),
        make_result("Lima", "significant", "falling"),
    ]

    _, summary = compare_places_summary(make_entry(), results)

    assert "falling significantly in Nairobi and Lima over" in summary


def test_opposite_ignores_places_without_a_significant_trend() -> None:
    results = [
        make_result("Helsinki", "significant", "rising"),
        make_result("Oslo", "not_significant", "rising"),
        make_result("Nairobi", "significant", "falling"),
    ]

    contrast, summary = compare_places_summary(make_entry(), results)

    assert contrast == "opposite_directions"
    assert "rising significantly in Helsinki and falling" in summary


def test_all_significant_rises_are_the_same_direction() -> None:
    results = [
        make_result("Helsinki", "significant", "rising"),
        make_result("Oslo", "significant", "rising"),
        make_result("Riga", "significant", "rising"),
    ]

    contrast, summary = compare_places_summary(make_entry(), results)

    assert contrast == "same_direction"
    assert summary == "Air temperature is rising significantly in all 3 places."


def test_all_significant_falls_are_the_same_direction() -> None:
    results = [
        make_result("Helsinki", "significant", "falling"),
        make_result("Oslo", "significant", "falling"),
        make_result("Riga", "significant", "falling"),
        make_result("Tallinn", "significant", "falling"),
    ]

    contrast, summary = compare_places_summary(make_entry(), results)

    assert contrast == "same_direction"
    assert summary == "Air temperature is falling significantly in all 4 places."


def test_same_direction_in_two_places_reads_both_places() -> None:
    results = [
        make_result("Helsinki", "significant", "falling"),
        make_result("Oslo", "significant", "falling"),
    ]

    contrast, summary = compare_places_summary(make_entry(), results)

    assert contrast == "same_direction"
    assert summary == "Air temperature is falling significantly in both places."


def test_a_place_without_a_significant_trend_makes_the_contrast_unclear() -> None:
    results = [
        make_result("Helsinki", "significant", "rising"),
        make_result("Oslo", "not_significant", "rising"),
    ]

    contrast, summary = compare_places_summary(make_entry(), results)

    assert contrast == "unclear"
    assert summary == (
        "Air temperature does not show a significant trend in every place, "
        "so the places cannot be clearly contrasted."
    )


def test_not_significant_fall_never_counts_as_opposite() -> None:
    results = [
        make_result("Helsinki", "significant", "rising"),
        make_result("Nairobi", "not_significant", "falling"),
    ]

    contrast, _ = compare_places_summary(make_entry(), results)

    assert contrast == "unclear"


def test_places_without_a_trend_make_the_contrast_unclear() -> None:
    results = [
        make_result("Helsinki", "too_few_years", None),
        make_result("Mid-Pacific", "no_data", None),
    ]

    contrast, _ = compare_places_summary(make_entry(), results)

    assert contrast == "unclear"


def test_comparison_needs_two_places() -> None:
    with pytest.raises(ValueError):
        compare_places_summary(make_entry(), [make_result("Helsinki", "significant", "rising")])
