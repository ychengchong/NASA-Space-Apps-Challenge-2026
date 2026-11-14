"""Record years (spec 7, "Record years"): descriptive facts about the years a case used."""

import pytest

from app.catalogue import get_entry
from app.models import ComparePlacesInput, RecordYear, YearsMean
from app.stats import all_equal, first_and_last_means, rank_years
from app.tools import trends
from app.tools.trends import compare_places
from app.verdict import RECORDS_NOTE, records_sentences
from tests.fake_source import FakeSource, line, monthly_from_yearly
from tests.test_tools import (
    HELSINKI,
    HELSINKI_GRID_POINT,
    NAIROBI,
    NAIROBI_GRID_POINT,
    analyse,
    context,
)

AIR_TEMP = get_entry("air_temp")
SOIL = get_entry("surface_soil_wetness")
YEARS = list(range(1981, 2026))


# Ranking (stats.rank_years)


def test_highest_years_are_listed_highest_first() -> None:
    ranked = rank_years([2000, 2001, 2002, 2003], [1.0, 4.0, 3.0, 2.0], highest=True)

    assert ranked.years == (2001, 2002, 2003)
    assert ranked.values == (4.0, 3.0, 2.0)
    assert ranked.tied == 0


def test_lowest_years_are_listed_lowest_first() -> None:
    ranked = rank_years([2000, 2001, 2002, 2003], [1.0, 4.0, 3.0, 2.0], highest=False)

    assert ranked.years == (2000, 2003, 2002)


def test_equal_values_are_listed_earliest_year_first() -> None:
    ranked = rank_years([2000, 2001, 2002, 2003], [5.0, 5.0, 1.0, 5.0], highest=True)

    assert ranked.years == (2000, 2001, 2003)
    assert ranked.tied == 0


def test_years_left_out_with_the_third_value_are_counted_as_tied() -> None:
    ranked = rank_years(
        [2000, 2001, 2002, 2003, 2004, 2005], [9.0, 7.0, 5.0, 5.0, 5.0, 1.0], highest=True
    )

    assert ranked.years == (2000, 2001, 2002)
    assert ranked.tied == 2


def test_the_lowest_value_is_never_listed_among_the_highest() -> None:
    years = list(range(1981, 2026))
    values = [0.004 if year == 2011 else 0.0 for year in years]

    highest = rank_years(years, values, highest=True)
    lowest = rank_years(years, values, highest=False)

    assert highest.years == (2011,)
    assert highest.tied == 0
    assert lowest.years == (1981, 1982, 1983)
    assert lowest.tied == 41


def test_the_highest_value_is_never_listed_among_the_lowest() -> None:
    years = list(range(1981, 2026))
    values = [0.0 if year in (1990, 2000) else 1.0 for year in years]

    lowest = rank_years(years, values, highest=False)
    highest = rank_years(years, values, highest=True)

    assert lowest.years == (1990, 2000)
    assert highest.years == (1981, 1982, 1983)
    assert highest.tied == 40


@pytest.mark.parametrize(
    "values",
    [
        [0.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 10.0],
        [0.0] + [5.0] * 43 + [10.0],
        [0.0] * 8 + [1.0, 2.0],
        [5.0] * 5 + [1.0] * 5,
        [3.0, 3.0, 2.0, 2.0, 1.0, 1.0, 1.0, 2.0, 3.0, 4.0],
        [float(k % 3) for k in range(12)],
    ],
)
def test_ten_or_more_values_never_put_a_year_in_both_lists(values: list[float]) -> None:
    years = list(range(2000, 2000 + len(values)))

    highest = rank_years(years, values, highest=True)
    lowest = rank_years(years, values, highest=False, exclude=highest.years)

    assert not set(highest.years) & set(lowest.years)


def test_rounding_residue_does_not_separate_equal_values() -> None:
    ranked = rank_years([2000, 2001, 2002, 2003], [0.1 + 0.2, 0.3, 0.0, 0.3], highest=True)

    assert ranked.years == (2000, 2001, 2003)


def test_a_record_of_fewer_values_lists_every_year_above_the_lowest() -> None:
    ranked = rank_years([2000, 2001, 2002], [1.0, 2.0, 3.0], highest=True)

    assert ranked.years == (2002, 2001)
    assert ranked.tied == 0


def test_rank_years_needs_one_value_per_year() -> None:
    with pytest.raises(ValueError):
        rank_years([2000, 2001], [1.0], highest=True)


def test_all_equal_sees_values_as_the_trend_test_does() -> None:
    assert all_equal([0.1 + 0.2, 0.3, 0.3])
    assert not all_equal([0.3, 0.31])


# The first and the last ten years (stats.first_and_last_means)


def test_first_and_last_ten_years_are_averaged_with_their_years() -> None:
    values = [float(year - 1981) for year in YEARS]

    windows = first_and_last_means(YEARS, values)

    assert windows is not None
    assert windows.first_years == tuple(range(1981, 1991))
    assert windows.last_years == tuple(range(2016, 2026))
    assert windows.first_mean == pytest.approx(4.5)
    assert windows.last_mean == pytest.approx(39.5)
    assert windows.change == pytest.approx(35.0)


def test_fewer_than_twenty_years_have_no_window_comparison() -> None:
    assert first_and_last_means(list(range(2000, 2019)), [1.0] * 19) is None


def test_twenty_years_split_into_two_windows_that_share_no_year() -> None:
    windows = first_and_last_means(list(range(2000, 2020)), [1.0] * 10 + [2.0] * 10)

    assert windows is not None
    assert windows.first_years[-1] == 2009
    assert windows.last_years[0] == 2010
    assert windows.change == pytest.approx(1.0)


def test_a_window_skips_a_missing_year_and_spans_one_more_year() -> None:
    years = [year for year in range(1981, 2006) if year != 1985]

    windows = first_and_last_means(years, [1.0] * len(years))

    assert windows is not None
    assert windows.first_years == (1981, 1982, 1983, 1984, 1986, 1987, 1988, 1989, 1990, 1991)


def test_equal_window_means_give_an_exact_zero_change() -> None:
    values = [0.1 + 0.2] * 10 + [0.3] * 10

    windows = first_and_last_means(list(range(2000, 2020)), values)

    assert windows is not None
    assert windows.change == 0.0


# Sentences (verdict.records_sentences)


def years_mean(first: int, mean: float) -> YearsMean:
    return YearsMean(years=list(range(first, first + 10)), mean=mean)


def test_sentences_list_the_highest_and_lowest_values_with_units_and_decimals() -> None:
    sentences = records_sentences(
        AIR_TEMP,
        [RecordYear(year=2020, value=8.264), RecordYear(year=2025, value=7.87)],
        [RecordYear(year=1987, value=-2.881)],
        0,
        0,
        None,
        None,
        None,
    )

    assert sentences == [
        "Highest yearly values used (°C): 8.26 in 2020 and 7.87 in 2025.",
        "Lowest yearly values used (°C): -2.88 in 1987.",
    ]


def test_sentence_counts_the_years_tied_with_the_last_listed_value() -> None:
    one, many = (
        records_sentences(
            AIR_TEMP,
            [RecordYear(year=2020, value=1.0)],
            [RecordYear(year=1990, value=0.0)],
            1,
            tied,
            None,
            None,
            None,
        )
        for tied in (1, 30)
    )

    assert one[0].endswith("1.00 in 2020. 1 more year has the same value as 2020.")
    assert many[1].endswith("0.00 in 1990. 30 more years have the same value as 1990.")


def test_window_sentence_says_higher_or_lower_with_the_rate_units() -> None:
    record = [RecordYear(year=2020, value=1.0)]
    higher, lower = (
        records_sentences(
            AIR_TEMP,
            record,
            record,
            0,
            0,
            years_mean(1981, 1.0),
            years_mean(2016, 1.0 + change),
            change,
        )[-1]
        for change in (1.123, -0.5)
    )

    assert higher == (
        "The mean of the last ten years used, 2016 to 2025, was 1.12 °C higher than the mean "
        "of the first ten, 1981 to 1990."
    )
    assert lower.endswith("was 0.50 °C lower than the mean of the first ten, 1981 to 1990.")


def test_window_sentence_says_the_same_for_an_exact_zero_change() -> None:
    record = [RecordYear(year=2020, value=1.0)]

    sentence = records_sentences(
        AIR_TEMP, record, record, 0, 0, years_mean(1981, 1.0), years_mean(2016, 1.0), 0.0
    )[-1]

    assert "was the same as the mean of the first ten" in sentence


def test_window_sentence_keeps_a_tiny_change_from_reading_as_zero() -> None:
    record = [RecordYear(year=2020, value=1.0)]

    sentence = records_sentences(
        AIR_TEMP, record, record, 0, 0, years_mean(1981, 1.0), years_mean(2016, 1.004), 0.004
    )[-1]

    assert "was 0.004 °C higher" in sentence


def test_a_variable_without_rate_units_states_the_change_as_a_bare_number() -> None:
    record = [RecordYear(year=2020, value=0.3)]

    sentences = records_sentences(
        SOIL, record, record, 0, 0, years_mean(1981, 0.3), years_mean(2016, 0.312), 0.012
    )

    assert sentences[0] == "Highest yearly values used (fraction, 0 to 1): 0.300 in 2020."
    assert "was 0.012 higher than" in sentences[-1]


def test_every_year_with_one_value_gives_one_sentence_and_ranks_nothing() -> None:
    sentences = records_sentences(AIR_TEMP, [], [], 0, 0, None, None, None, same_value=1.0)

    assert sentences == ["Every year used has the same value (°C): 1.00."]


def test_no_sentence_and_no_note_calls_a_record_significant() -> None:
    record = [RecordYear(year=2020, value=1.0)]
    sentences = records_sentences(
        AIR_TEMP, record, record, 0, 0, years_mean(1981, 1.0), years_mean(2016, 2.0), 1.0
    )

    assert all("significant" not in sentence for sentence in sentences)
    assert "significance was not assessed" in RECORDS_NOTE
    assert "not tests" in RECORDS_NOTE


# The records of a case (tools)


@pytest.mark.anyio
async def test_a_case_lists_its_record_years_with_the_note() -> None:
    yearly = line(0.05)
    yearly[1990] = 99.0
    source = FakeSource(monthly_from_yearly(yearly))

    (result,) = (await analyse(source)).results

    assert result.records is not None
    assert result.records.highest[0].year == 1990
    assert result.records.highest[0].value == pytest.approx(99.0)
    assert [item.year for item in result.records.lowest] == [1981, 1982, 1983]
    assert result.records.first_ten is not None
    assert result.records.first_ten.years == list(range(1981, 1991))
    assert result.records.last_ten is not None
    assert result.records.last_ten.years == list(range(2016, 2026))
    assert result.records.note == RECORDS_NOTE
    assert len(result.records.sentences) == 3


@pytest.mark.anyio
async def test_a_year_with_a_missing_month_is_never_a_record() -> None:
    monthly = monthly_from_yearly(line(0.05))
    monthly[(2025, 6)] = None
    monthly[(2024, 1)] = None
    source = FakeSource(monthly)

    (result,) = (await analyse(source)).results

    assert result.records is not None
    assert [item.year for item in result.records.highest] == [2023, 2022, 2021]
    assert result.records.last_ten is not None
    assert result.records.last_ten.years == list(range(2014, 2024))


@pytest.mark.anyio
async def test_a_short_record_has_no_records() -> None:
    source = FakeSource(monthly_from_yearly(line(0.05, first_year=2020)))

    (result,) = (await analyse(source)).results

    assert result.verdict.kind == "too_few_years"
    assert result.records is None


@pytest.mark.anyio
async def test_a_place_with_no_data_has_no_records() -> None:
    source = FakeSource(monthly_from_yearly(dict.fromkeys(YEARS, None)))

    (result,) = (await analyse(source)).results

    assert result.verdict.kind == "no_data"
    assert result.records is None


@pytest.mark.anyio
async def test_constant_values_rank_nothing_and_say_every_year_is_the_same() -> None:
    source = FakeSource(monthly_from_yearly(dict.fromkeys(YEARS, 1.0)))

    (result,) = (await analyse(source)).results

    assert result.records is not None
    assert result.records.highest == []
    assert result.records.lowest == []
    assert result.records.sentences == ["Every year used has the same value (°C): 1.00."]
    assert result.records.change == 0.0


@pytest.mark.anyio
async def test_a_record_of_fifteen_years_ranks_years_but_compares_no_windows() -> None:
    source = FakeSource(monthly_from_yearly(line(0.05, first_year=2011)))

    (result,) = (await analyse(source, **{"from": 2011})).results

    assert result.records is not None
    assert len(result.records.highest) == 3
    assert result.records.first_ten is None
    assert result.records.change is None
    assert len(result.records.sentences) == 2


@pytest.mark.anyio
async def test_a_comparison_ranks_only_the_common_years() -> None:
    helsinki = line(0.05)
    nairobi: dict[int, float | None] = dict(line(0.05))
    nairobi[2025] = None
    source = FakeSource(
        by_point={
            HELSINKI_GRID_POINT: monthly_from_yearly(helsinki),
            NAIROBI_GRID_POINT: monthly_from_yearly(nairobi),
        }
    )
    inp = ComparePlacesInput.model_validate({"variable": "air_temp", "places": [HELSINKI, NAIROBI]})

    investigation = await compare_places(inp, context(source))

    for result in investigation.results:
        assert result.records is not None
        assert 2025 not in [item.year for item in result.records.highest]
        assert result.records.last_ten is not None
        assert result.records.last_ten.years[-1] == 2024


@pytest.mark.anyio
async def test_records_do_not_change_the_investigation_id(monkeypatch: pytest.MonkeyPatch) -> None:
    source = FakeSource(monthly_from_yearly(line(0.05)))
    with_records = await analyse(source)
    monkeypatch.setattr(trends, "_records", lambda *_: None)

    without_records = await analyse(source)

    assert with_records.results[0].records is not None
    assert without_records.results[0].records is None
    assert without_records.id == with_records.id


def test_a_middle_value_shared_by_many_years_is_listed_in_one_list_only() -> None:
    years = list(range(2000, 2010))
    values = [0.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 10.0]

    highest = rank_years(years, values, highest=True)
    lowest = rank_years(years, values, highest=False, exclude=highest.years)

    assert highest.years == (2009, 2001, 2002)
    assert lowest.years == (2000, 2003, 2004)
    assert lowest.tied == 4


def test_a_small_value_gets_more_digits_instead_of_reading_as_zero() -> None:
    sentences = records_sentences(
        get_entry("snow_depth"),
        [RecordYear(year=1985, value=0.00085)],
        [RecordYear(year=1990, value=-0.0003)],
        0,
        0,
        None,
        None,
        None,
    )

    assert sentences == [
        "Highest yearly values used (cm): 0.001 in 1985.",
        "Lowest yearly values used (cm): -0.0003 in 1990.",
    ]
