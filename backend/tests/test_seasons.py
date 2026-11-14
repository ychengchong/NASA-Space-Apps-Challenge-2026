"""All seasons at once (spec 7, "All seasons at once"): descriptive rates side by side."""

from pathlib import Path

import pytest

from app.cache import Cache
from app.models import PlaceInput, SeasonRatesInput
from app.services import Services
from app.tools.trends import SEASON_ORDER, analyze_trend, season_rates
from app.verdict import SEASONS_NOTE
from tests.app_client import make_services
from tests.fake_source import FakeSource, line, monthly_from_yearly
from tests.test_rest import client_for
from tests.test_tools import (
    HELSINKI,
    HELSINKI_GRID_POINT,
    NAIROBI,
    NAIROBI_GRID_POINT,
    context,
    trend_input,
)

pytestmark = pytest.mark.anyio

RISING = monthly_from_yearly(line(0.05))


def seasons_input(
    variable: str = "air_temp", places: tuple[PlaceInput, ...] = (HELSINKI,), **fields: object
) -> SeasonRatesInput:
    return SeasonRatesInput.model_validate({"variable": variable, "places": list(places), **fields})


async def test_rows_are_all_months_then_the_four_seasons_in_order() -> None:
    answer = await season_rates(seasons_input(), context(FakeSource(RISING)))

    (place,) = answer.places
    assert [rate.season for rate in place.rates] == list(SEASON_ORDER)
    assert answer.note == SEASONS_NOTE


async def test_each_row_has_the_rate_the_case_of_that_season_gives() -> None:
    source = FakeSource(RISING)
    answer = await season_rates(seasons_input(), context(source))

    for rate in answer.places[0].rates:
        case = await analyze_trend(trend_input(season=rate.season), context(source))
        trend = case.results[0].trend
        assert trend is not None
        assert rate.sen_slope == trend.sen_slope
        assert rate.total_change == trend.total_change
        assert (rate.first_year, rate.last_year, rate.n) == (
            trend.first_year,
            trend.last_year,
            trend.n,
        )


async def test_only_the_all_months_row_of_annual_air_temperature_is_assessed() -> None:
    answer = await season_rates(seasons_input(), context(FakeSource(RISING)))

    rates = answer.places[0].rates
    assert [rate.assessed for rate in rates] == [True, False, False, False, False]
    assert rates[0].verdict_kind == "significant"
    assert "The trend test for all months finds it significant." in rates[0].sentence
    assert all(rate.sentence.endswith("Significance was not assessed.") for rate in rates[1:])


async def test_no_row_of_another_variable_is_assessed() -> None:
    answer = await season_rates(seasons_input("precipitation"), context(FakeSource(RISING)))

    assert not any(rate.assessed for rate in answer.places[0].rates)
    assert all("not assessed" in rate.sentence for rate in answer.places[0].rates)


async def test_december_to_february_starts_a_year_later() -> None:
    answer = await season_rates(seasons_input(), context(FakeSource(RISING)))

    djf = answer.places[0].rates[1]
    assert (djf.first_year, djf.last_year, djf.n) == (1982, 2025, 44)


async def test_a_season_with_too_few_years_has_no_rate() -> None:
    source = FakeSource(monthly_from_yearly(line(0.05, first_year=2016)))

    answer = await season_rates(seasons_input(**{"from": 2016}), context(source))

    djf = answer.places[0].rates[1]
    assert djf.sen_slope is None
    assert djf.verdict_kind == "too_few_years"
    assert djf.sentence == "December to February: 9 complete years, too few for a rate."


async def test_a_comparison_gives_each_place_its_seasons_on_common_years() -> None:
    nairobi: dict[int, float | None] = dict(line(0.05))
    nairobi[2025] = None
    source = FakeSource(
        by_point={
            HELSINKI_GRID_POINT: RISING,
            NAIROBI_GRID_POINT: monthly_from_yearly(nairobi),
        }
    )

    answer = await season_rates(seasons_input(places=(HELSINKI, NAIROBI)), context(source))

    assert [place.place.name for place in answer.places] == ["Helsinki", "Nairobi"]
    for place in answer.places:
        assert all(rate.last_year == 2024 for rate in place.rates)


async def test_the_seasons_read_one_fetch_per_place() -> None:
    source = FakeSource(RISING)

    await season_rates(seasons_input(), context(source))

    assert len({(lat, lon) for lat, lon, _, _ in source.calls}) == 1


async def test_the_seasons_return_no_p_value_or_interval() -> None:
    answer = await season_rates(seasons_input(), context(FakeSource(RISING)))

    fields = set(answer.places[0].rates[0].model_dump())
    assert not fields & {"mk_p", "sen_ci95", "ols_p", "p"}


# /api/seasons


def test_seasons_endpoint_takes_the_case_parameters(tmp_path: Path) -> None:
    services = make_services_for(tmp_path)
    client = client_for(services, tmp_path)

    response = client.get(
        "/api/seasons?v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=DJF"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested"] == {"from": 1981, "to": 2025, "season": "DJF"}
    assert [rate["season"] for rate in body["places"][0]["rates"]] == list(SEASON_ORDER)


def test_case_endpoint_answers_as_before_without_seasons(tmp_path: Path) -> None:
    client = client_for(make_services_for(tmp_path), tmp_path)

    body = client.get("/api/case?v=air_temp&p=60.17,24.94&label=Helsinki").json()

    assert "places" not in body
    assert "seasons" not in body


def test_seasons_endpoint_refuses_a_case_without_a_place(tmp_path: Path) -> None:
    client = client_for(make_services_for(tmp_path), tmp_path)

    response = client.get("/api/seasons?v=air_temp")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_place"


def make_services_for(tmp_path: Path) -> Services:
    return make_services(Cache(tmp_path / "cache.sqlite"), FakeSource(RISING))


async def test_one_complete_year_is_named_in_the_singular() -> None:
    answer = await season_rates(
        seasons_input(**{"from": 2025, "to": 2025}), context(FakeSource(RISING))
    )

    assert answer.places[0].rates[0].sentence == "Every month: 1 complete year, too few for a rate."


async def test_a_season_without_common_years_says_so_for_a_place_that_has_data() -> None:
    no_january = {
        key: (None if key[1] == 1 else value)
        for key, value in monthly_from_yearly(line(0.05)).items()
    }
    source = FakeSource(by_point={HELSINKI_GRID_POINT: RISING, NAIROBI_GRID_POINT: no_january})

    answer = await season_rates(seasons_input(places=(HELSINKI, NAIROBI)), context(source))

    helsinki_annual = answer.places[0].rates[0]
    assert helsinki_annual.n == 0
    assert (
        helsinki_annual.sentence == "Every month: no complete year in common with the other places."
    )
