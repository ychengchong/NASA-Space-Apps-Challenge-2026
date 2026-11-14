"""The gap between two places (spec 7): descriptive, and never a test of the difference."""

import pytest

from app.catalogue import get_entry
from app.models import ComparePlacesInput, Investigation, PlaceInput
from app.stats import PER_DECADE, compute_trend
from app.tools import trends
from app.tools.trends import compare_places
from app.verdict import compare_places_summary
from tests.fake_source import FakeSource, line, monthly_from_yearly
from tests.test_tools import HELSINKI, HELSINKI_GRID_POINT, NAIROBI, NAIROBI_GRID_POINT, context

pytestmark = pytest.mark.anyio

KALLIO = PlaceInput(lat=60.18, lon=24.95, name="Kallio")


def source(helsinki: dict[int, float | None], nairobi: dict[int, float | None]) -> FakeSource:
    return FakeSource(
        by_point={
            HELSINKI_GRID_POINT: monthly_from_yearly(helsinki),
            NAIROBI_GRID_POINT: monthly_from_yearly(nairobi),
        }
    )


async def compare(fake: FakeSource, *places: PlaceInput) -> Investigation:
    inp = ComparePlacesInput.model_validate({"variable": "air_temp", "places": list(places)})
    return await compare_places(inp, context(fake))


async def test_the_gap_is_the_first_place_minus_the_second_in_each_common_year() -> None:
    nairobi: dict[int, float | None] = dict(line(0.02))
    nairobi[2000] = None
    investigation = await compare(source(dict(line(0.05)), nairobi), HELSINKI, NAIROBI)

    gap = investigation.gap
    assert gap is not None
    assert (gap.first_place, gap.second_place) == ("Helsinki", "Nairobi")
    assert 2000 not in [point.year for point in gap.series]
    assert gap.n == 44
    for point in gap.series:
        assert point.value == pytest.approx(0.03 * (point.year - 1981))


async def test_the_gap_rate_is_the_sen_rate_of_the_gap_series_itself() -> None:
    helsinki = {
        year: 10.0 + 0.05 * (year - 1981) + (0.3 if year % 3 == 0 else 0.0)
        for year in range(1981, 2026)
    }
    investigation = await compare(source(dict(helsinki), dict(line(0.01))), HELSINKI, NAIROBI)

    gap = investigation.gap
    assert gap is not None
    expected = compute_trend(
        [point.year for point in gap.series], [point.value or 0.0 for point in gap.series]
    )
    assert gap.sen_slope == pytest.approx(expected.sen_slope * PER_DECADE)


async def test_the_sentence_holds_when_both_places_fall() -> None:
    investigation = await compare(source(dict(line(-0.05)), dict(line(-0.02))), HELSINKI, NAIROBI)

    gap = investigation.gap
    assert gap is not None
    assert gap.sen_slope is not None and gap.sen_slope < 0
    assert gap.sentence.startswith(
        "The difference between Helsinki and Nairobi, Helsinki minus Nairobi, changed by about "
        "-0.30 °C per decade"
    )
    assert "faster" not in gap.sentence
    assert gap.sentence.endswith("The difference was not tested; this is a description.")


async def test_places_in_one_grid_cell_have_a_zero_gap_and_say_so() -> None:
    investigation = await compare(FakeSource(monthly_from_yearly(line(0.05))), HELSINKI, KALLIO)

    gap = investigation.gap
    assert gap is not None
    assert gap.same_cell
    assert all(point.value == 0.0 for point in gap.series)
    assert gap.sen_slope == 0.0
    assert gap.sentence == (
        "Helsinki and Kallio are in the same grid cell, so the difference between them is zero "
        "in every year."
    )


async def test_too_few_common_years_give_no_rate() -> None:
    short = dict(line(0.05, first_year=2018))
    investigation = await compare(source(short, dict(line(0.02))), HELSINKI, NAIROBI)

    gap = investigation.gap
    assert gap is not None
    assert gap.sen_slope is None
    assert gap.sentence == (
        "Helsinki and Nairobi have 8 common complete years, too few for a rate of their difference."
    )


async def test_a_comparison_of_three_places_has_no_gap() -> None:
    fake = FakeSource(monthly_from_yearly(line(0.05)))

    investigation = await compare(fake, HELSINKI, NAIROBI, KALLIO)

    assert investigation.gap is None


async def test_the_gap_leaves_the_summary_and_the_id_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = source(dict(line(0.05)), dict(line(0.02)))
    with_gap = await compare(fake, HELSINKI, NAIROBI)
    monkeypatch.setattr(trends, "_gap", lambda *_: None)

    without_gap = await compare(fake, HELSINKI, NAIROBI)

    assert with_gap.gap is not None
    assert without_gap.id == with_gap.id
    assert with_gap.summary == compare_places_summary(get_entry("air_temp"), with_gap.results)[1]


async def test_the_gap_carries_no_p_value_or_interval() -> None:
    investigation = await compare(source(dict(line(0.05)), dict(line(0.02))), HELSINKI, NAIROBI)

    assert investigation.gap is not None
    assert not set(investigation.gap.model_dump()) & {"mk_p", "sen_ci95", "ols_p", "p"}
