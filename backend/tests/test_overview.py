"""What is changing here? (spec 7): every catalogue variable's descriptive rate at one place."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from app.cache import Cache
from app.catalogue import load_catalogue
from app.errors import BadPeriodError
from app.models import PlaceOverviewInput
from app.sources.power import PowerClient
from app.tools.context import ToolContext
from app.tools.trends import place_overview
from app.verdict import OVERVIEW_NOTE
from tests.app_client import make_services
from tests.fake_source import FakeSource, line, monthly_from_yearly
from tests.test_rest import client_for
from tests.test_tools import FIXTURES, HELSINKI, LAST_COMPLETE_YEAR, context

pytestmark = pytest.mark.anyio

RISING = monthly_from_yearly(line(0.05))


def overview_input(**fields: object) -> PlaceOverviewInput:
    return PlaceOverviewInput.model_validate({"place": HELSINKI, **fields})


async def test_every_catalogue_variable_has_one_row_in_catalogue_order() -> None:
    overview = await place_overview(overview_input(), context(FakeSource(RISING)))

    assert [row.variable.id for row in overview.rows] == [entry.id for entry in load_catalogue()]
    assert overview.note == OVERVIEW_NOTE


async def test_only_annual_air_temperature_is_assessed() -> None:
    overview = await place_overview(overview_input(), context(FakeSource(RISING)))

    assessed = [row.variable.id for row in overview.rows if row.assessed]
    assert assessed == ["air_temp"]
    assert all(
        row.sentence.endswith("Significance was not assessed.")
        for row in overview.rows
        if not row.assessed
    )


async def test_each_variable_runs_over_its_own_record_within_the_period() -> None:
    overview = await place_overview(overview_input(), context(FakeSource(RISING)))

    by_id = {row.variable.id: row for row in overview.rows}
    assert (by_id["air_temp"].first_year, by_id["air_temp"].last_year) == (1981, 2025)
    assert by_id["haze"].first_year == 2001
    assert by_id["sunlight"].first_year == 1984


async def test_a_period_before_a_record_starts_gives_a_row_without_years() -> None:
    overview = await place_overview(
        overview_input(**{"from": 1981, "to": 1995}), context(FakeSource(RISING))
    )

    haze = next(row for row in overview.rows if row.variable.id == "haze")
    assert haze.n == 0
    assert haze.sen_slope is None
    assert haze.sentence == "Its record starts in 2001, after the period ends."


async def test_a_row_names_its_rate_total_years_and_record_years() -> None:
    overview = await place_overview(overview_input(), context(FakeSource(RISING)))

    air = overview.rows[0]
    assert air.sentence.startswith(
        "+0.50 °C per decade from 1981 to 2025, +2.20 °C in all, over 45 complete years; "
        "highest in 2025, lowest in 1981."
    )
    assert (air.highest_year, air.lowest_year) == (2025, 1981)


async def test_a_period_before_any_record_is_refused() -> None:
    with pytest.raises(BadPeriodError):
        await place_overview(overview_input(**{"from": 1970}), context(FakeSource(RISING)))


async def test_rows_carry_no_p_value_or_interval() -> None:
    overview = await place_overview(overview_input(), context(FakeSource(RISING)))

    assert not set(overview.rows[0].model_dump()) & {"mk_p", "sen_ci95", "ols_p"}


async def test_a_new_place_costs_one_call_per_grid_and_a_cached_place_none(
    tmp_path: Path,
) -> None:
    payload = json.loads((FIXTURES / "power_point_all_codes.json").read_text(encoding="utf-8"))
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    cache = Cache(tmp_path / "cache.sqlite")
    client = PowerClient(
        cache,
        httpx.AsyncClient(transport=httpx.MockTransport(answer)),
        today=lambda: date(2026, 11, 13),
    )
    try:
        ctx = ToolContext(source=client, last_complete_year=LAST_COMPLETE_YEAR)
        await place_overview(overview_input(), ctx)
        first = len(requests)
        await place_overview(overview_input(), ctx)
    finally:
        await client.aclose()
        cache.close()

    assert first == 2
    assert len(requests) == first


# /api/overview


def test_overview_endpoint_takes_one_place_and_the_period(tmp_path: Path) -> None:
    services = make_services(Cache(tmp_path / "cache.sqlite"), FakeSource(RISING))
    client = client_for(services, tmp_path)

    response = client.get("/api/overview?p=60.17,24.94&label=Helsinki&from=1990&to=2025")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Helsinki"
    assert body["requested"] == {"from": 1990, "to": 2025, "season": "annual"}
    assert body["app_url"].endswith(
        "/place?p=60.17,24.94&label=Helsinki&from=1990&to=2025&s=annual"
    )


def test_overview_endpoint_refuses_two_places(tmp_path: Path) -> None:
    services = make_services(Cache(tmp_path / "cache.sqlite"), FakeSource(RISING))
    client = client_for(services, tmp_path)

    response = client.get("/api/overview?p=60.17,24.94&p=1,2")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_place"
