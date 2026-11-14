import asyncio
import concurrent.futures
import gc
import json
import threading
from collections.abc import Awaitable, Callable, Coroutine, Iterator, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.cache import Cache
from app.catalogue import GridAlignment, load_catalogue
from app.errors import SourceUnavailableError
from app.models import Box
from app.sources import power as power_module
from app.sources.base import PointSeries
from app.sources.power import (
    CODES_ON_ONE_DEGREE_GRID,
    NOT_ANSWERING_MESSAGE,
    PAUSED_MESSAGE,
    POINT_PATH,
    REGIONAL_PATH,
    REJECTED_MESSAGE,
    RETRY_DELAY_SECONDS,
    UNREADABLE_MESSAGE,
    PowerClient,
    parse_monthly,
)

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 13)
END_YEAR = 2025
LAT, LON = 60.0, 25.0
YEARS_IN_FULL_FIXTURE = 2025 - 1981 + 1


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


FULL = load_fixture("power_point_full.json")
GAP = load_fixture("power_point_gap.json")
REGIONAL = load_fixture("power_regional.json")


def point_payload(codes: Sequence[str]) -> dict[str, Any]:
    """The saved full-record response cut down to `codes`, as POWER sends it for those codes."""
    return {
        **FULL,
        "properties": {
            "parameter": {code: FULL["properties"]["parameter"][code] for code in codes}
        },
        "parameters": {code: FULL["parameters"][code] for code in codes},
    }


def codes_of(request: httpx.Request) -> list[str]:
    return request.url.params["parameters"].split(",")


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakeSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class FakePower:
    """Stands in for POWER: answers from the saved response after the given failures.

    A failure is an HTTP status to answer with, or an httpx exception class to raise.
    """

    def __init__(self, failures: Sequence[int | type[httpx.HTTPError]] = ()) -> None:
        self.requests: list[httpx.Request] = []
        self._failures = list(failures)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._failures:
            failure = self._failures.pop(0)
            if isinstance(failure, int):
                return httpx.Response(failure, text="simulated failure")
            raise failure("simulated failure", request=request)
        return httpx.Response(200, json=point_payload(codes_of(request)))


class GatedPower:
    """Holds every call until `release()` and records how many were open at once."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.open_calls = 0
        self.most_open_calls = 0
        self._gate = asyncio.Event()

    def release(self) -> None:
        self._gate.set()

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.open_calls += 1
        self.most_open_calls = max(self.most_open_calls, self.open_calls)
        await self._gate.wait()
        self.open_calls -= 1
        return httpx.Response(200, json=point_payload(codes_of(request)))


Handler = Callable[[httpx.Request], httpx.Response | Awaitable[httpx.Response]]


def make_client(
    handler: Handler,
    cache: Cache,
    clock: FakeClock | None = None,
    sleep: FakeSleep | None = None,
) -> PowerClient:
    return PowerClient(
        cache,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        clock=clock or FakeClock(),
        today=lambda: TODAY,
        sleep=sleep or FakeSleep(),
    )


async def let_tasks_run() -> None:
    for _ in range(50):
        await asyncio.sleep(0)


# Long enough for any passing scenario, short enough that a hang fails the test run quickly.
SCENARIO_TIME_LIMIT_SECONDS = 10.0


def run_with_time_limit[T](scenario: Coroutine[Any, Any, T]) -> T:
    """Run `scenario` on its own event loop in another thread, and fail if it has not ended.

    A coroutine that loops without ever awaiting blocks its event loop, so no asyncio timeout
    can stop it. Waiting from another thread turns such a hang into a failed test.
    """
    outcome: concurrent.futures.Future[T] = concurrent.futures.Future()

    def run() -> None:
        try:
            outcome.set_result(asyncio.run(scenario))
        except Exception as error:
            outcome.set_exception(error)

    threading.Thread(target=run, daemon=True).start()
    try:
        return outcome.result(SCENARIO_TIME_LIMIT_SECONDS)
    except TimeoutError:
        pytest.fail(f"the scenario did not end within {SCENARIO_TIME_LIMIT_SECONDS} s")


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[Cache]:
    opened = Cache(tmp_path / "cache.sqlite")
    yield opened
    opened.close()


# Parsing


async def test_fill_value_becomes_none(cache: Cache) -> None:
    client = make_client(FakePower(), cache)
    series = (await client.point_series(LAT, LON, ["ALLSKY_SFC_SW_DWN"], END_YEAR))[
        "ALLSKY_SFC_SW_DWN"
    ]
    assert series.monthly[(1983, 12)] is None
    assert series.monthly[(1984, 1)] == 0.92
    assert -999.0 not in series.monthly.values()


async def test_month_13_is_ignored(cache: Cache) -> None:
    client = make_client(FakePower(), cache)
    series = (await client.point_series(LAT, LON, ["T2M"], END_YEAR))["T2M"]
    assert {month for _, month in series.monthly} == set(range(1, 13))
    assert len(series.monthly) == 12 * YEARS_IN_FULL_FIXTURE


async def test_series_carries_grid_point_version_and_access_date(cache: Cache) -> None:
    client = make_client(FakePower(), cache)
    series = (await client.point_series(LAT, LON, ["T2M"], END_YEAR))["T2M"]
    assert (series.code, series.lat, series.lon) == ("T2M", LAT, LON)
    assert series.version == "v2.10.0"
    assert series.accessed == "2026-11-13"


async def test_gap_fixture_has_exactly_one_missing_month(cache: Cache) -> None:
    client = make_client(lambda _: httpx.Response(200, json=GAP), cache)
    monthly = (await client.point_series(LAT, LON, ["T2M"], END_YEAR))["T2M"].monthly
    assert len(monthly) == 72
    assert [key for key, value in monthly.items() if value is None] == [(2002, 12)]
    assert monthly[(2002, 11)] == -0.6


def test_parse_monthly_treats_null_as_missing() -> None:
    values = {"198101": None, "198102": -999.0, "198103": 1.5, "198113": 4.0}
    assert parse_monthly(values, -999.0) == {(1981, 1): None, (1981, 2): None, (1981, 3): 1.5}


def test_parse_monthly_rejects_a_key_that_is_not_a_month() -> None:
    with pytest.raises(ValueError):
        parse_monthly({"198114": 1.0}, -999.0)


def test_parse_monthly_rejects_values_that_are_not_an_object() -> None:
    with pytest.raises(TypeError):
        parse_monthly([1.0, 2.0], -999.0)


async def test_point_values_that_are_not_an_object_raise_source_unavailable(
    cache: Cache,
) -> None:
    payload = point_payload(["T2M"])
    payload["properties"]["parameter"]["T2M"] = [1.0, 2.0]
    client = make_client(lambda _: httpx.Response(200, json=payload), cache)
    with pytest.raises(SourceUnavailableError) as error:
        await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == UNREADABLE_MESSAGE


# Soil wetness over open ocean


def with_values(
    payload: dict[str, Any], code: str, change: Callable[[dict[str, float]], dict[str, float]]
) -> dict[str, Any]:
    """`payload` with the values of `code` replaced by `change` applied to a copy of them."""
    parameter = payload["properties"]["parameter"]
    parameter[code] = change(dict(parameter[code]))
    return payload


def ocean_soil_payload() -> dict[str, Any]:
    """The saved response with both soil wetness codes as POWER sends them over open ocean."""
    payload = point_payload(["GWETTOP", "GWETROOT"])
    payload = with_values(payload, "GWETTOP", lambda values: dict.fromkeys(values, 1.0))
    return with_values(payload, "GWETROOT", lambda values: dict.fromkeys(values, -999.0))


async def test_soil_wetness_that_is_one_in_every_month_becomes_missing(cache: Cache) -> None:
    client = make_client(lambda _: httpx.Response(200, json=ocean_soil_payload()), cache)
    result = await client.point_series(LAT, LON, ["GWETTOP", "GWETROOT"], END_YEAR)
    for code in ("GWETTOP", "GWETROOT"):
        assert len(result[code].monthly) == 12 * YEARS_IN_FULL_FIXTURE
        assert set(result[code].monthly.values()) == {None}


async def test_soil_wetness_from_the_ocean_is_cached_as_missing(cache: Cache) -> None:
    ocean = make_client(lambda _: httpx.Response(200, json=ocean_soil_payload()), cache)
    await ocean.point_series(LAT, LON, ["GWETTOP"], END_YEAR)
    power = FakePower()
    series = (await make_client(power, cache).point_series(LAT, LON, ["GWETTOP"], END_YEAR))[
        "GWETTOP"
    ]
    assert set(series.monthly.values()) == {None}
    assert power.requests == []


async def test_soil_wetness_that_is_one_whenever_reported_becomes_missing(cache: Cache) -> None:
    def ocean_with_gaps(values: dict[str, float]) -> dict[str, float]:
        return {key: -999.0 if key.startswith("1981") else 1.0 for key in values}

    payload = with_values(point_payload(["GWETTOP"]), "GWETTOP", ocean_with_gaps)
    client = make_client(lambda _: httpx.Response(200, json=payload), cache)
    series = (await client.point_series(LAT, LON, ["GWETTOP"], END_YEAR))["GWETTOP"]
    assert set(series.monthly.values()) == {None}


async def test_land_soil_wetness_that_is_one_in_some_months_is_kept(cache: Cache) -> None:
    def saturate_early_1981(values: dict[str, float]) -> dict[str, float]:
        return {**values, "198101": 1.0, "198102": 1.0}

    payload = with_values(point_payload(["GWETTOP"]), "GWETTOP", saturate_early_1981)
    client = make_client(lambda _: httpx.Response(200, json=payload), cache)
    monthly = (await client.point_series(LAT, LON, ["GWETTOP"], END_YEAR))["GWETTOP"].monthly
    assert monthly[(1981, 1)] == 1.0
    assert monthly[(1981, 3)] == FULL["properties"]["parameter"]["GWETTOP"]["198103"]
    assert None not in monthly.values()


async def test_other_codes_that_are_one_in_every_month_are_kept(cache: Cache) -> None:
    payload = with_values(point_payload(["T2M"]), "T2M", lambda values: dict.fromkeys(values, 1.0))
    client = make_client(lambda _: httpx.Response(200, json=payload), cache)
    series = (await client.point_series(LAT, LON, ["T2M"], END_YEAR))["T2M"]
    assert set(series.monthly.values()) == {1.0}


async def test_point_call_asks_for_the_full_record(cache: Cache) -> None:
    power = FakePower()
    client = make_client(power, cache)
    await client.point_series(LAT, LON, ["T2M", "PRECTOTCORR"], END_YEAR)
    (request,) = power.requests
    assert request.url.host == "power.larc.nasa.gov"
    assert request.url.path == POINT_PATH
    assert dict(request.url.params) == {
        "parameters": "T2M,PRECTOTCORR",
        "community": "AG",
        "latitude": "60.0",
        "longitude": "25.0",
        "start": "1981",
        "end": "2025",
        "format": "JSON",
    }


async def test_more_than_twenty_codes_are_split_across_calls(cache: Cache) -> None:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        parameter = {code: {"198101": 1.0} for code in codes_of(request)}
        return httpx.Response(
            200, json={"header": FULL["header"], "properties": {"parameter": parameter}}
        )

    codes = [f"CODE{number}" for number in range(25)]
    result = await make_client(answer, cache).point_series(LAT, LON, codes, END_YEAR)
    assert list(result) == codes
    assert [len(codes_of(request)) for request in requests] == [20, 5]


# Caching


async def test_cache_hit_makes_no_call(cache: Cache) -> None:
    power = FakePower()
    client = make_client(power, cache)
    first = await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    second = await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    assert second == first
    assert len(power.requests) == 1


async def test_cached_values_survive_a_new_client(cache: Cache) -> None:
    await make_client(FakePower(), cache).point_series(LAT, LON, ["T2M"], END_YEAR)
    power = FakePower()
    await make_client(power, cache).point_series(LAT, LON, ["T2M"], END_YEAR)
    assert power.requests == []


async def test_only_missing_codes_are_requested(cache: Cache) -> None:
    power = FakePower()
    client = make_client(power, cache)
    await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    result = await client.point_series(LAT, LON, ["T2M", "PRECTOTCORR", "TS"], END_YEAR)
    assert list(result) == ["T2M", "PRECTOTCORR", "TS"]
    assert codes_of(power.requests[-1]) == ["PRECTOTCORR", "TS"]


async def test_series_cached_to_an_earlier_year_is_fetched_again(cache: Cache) -> None:
    power = FakePower()
    client = make_client(power, cache)
    await client.point_series(LAT, LON, ["T2M"], 2024)
    await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    assert [request.url.params["end"] for request in power.requests] == ["2024", "2025"]


async def test_months_after_end_year_are_left_out(cache: Cache) -> None:
    power = FakePower()
    client = make_client(power, cache)
    await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    series = (await client.point_series(LAT, LON, ["T2M"], 2020))["T2M"]
    assert max(year for year, _ in series.monthly) == 2020
    assert len(power.requests) == 1


# Failures


async def test_retries_once_after_a_server_error(cache: Cache) -> None:
    power, sleep = FakePower(failures=[503]), FakeSleep()
    client = make_client(power, cache, sleep=sleep)
    result = await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    assert set(result) == {"T2M"}
    assert len(power.requests) == 2
    assert sleep.delays == [RETRY_DELAY_SECONDS]


async def test_retries_once_after_a_timeout(cache: Cache) -> None:
    power, sleep = FakePower(failures=[httpx.ReadTimeout]), FakeSleep()
    client = make_client(power, cache, sleep=sleep)
    result = await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    assert set(result) == {"T2M"}
    assert len(power.requests) == 2
    assert sleep.delays == [RETRY_DELAY_SECONDS]


async def test_second_server_error_raises_source_unavailable(cache: Cache) -> None:
    power = FakePower(failures=[500, 502])
    with pytest.raises(SourceUnavailableError) as error:
        await make_client(power, cache).point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == NOT_ANSWERING_MESSAGE
    assert len(power.requests) == 2


async def test_second_timeout_raises_source_unavailable(cache: Cache) -> None:
    power = FakePower(failures=[httpx.ConnectTimeout, httpx.ReadTimeout])
    with pytest.raises(SourceUnavailableError) as error:
        await make_client(power, cache).point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == NOT_ANSWERING_MESSAGE
    assert len(power.requests) == 2


async def test_call_running_past_the_time_limit_is_retried_once(
    cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The real 20 s limit is shortened so the test runs quickly; the answer comes later still.
    monkeypatch.setattr(power_module, "CALL_TIMEOUT_SECONDS", 0.01)
    requests: list[httpx.Request] = []

    async def answer_late(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        await asyncio.sleep(1.0)
        return httpx.Response(200, json=point_payload(codes_of(request)))

    sleep = FakeSleep()
    with pytest.raises(SourceUnavailableError) as error:
        await make_client(answer_late, cache, sleep=sleep).point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == NOT_ANSWERING_MESSAGE
    assert len(requests) == 2
    assert sleep.delays == [RETRY_DELAY_SECONDS]


async def test_connection_error_raises_a_plain_message_without_retry(cache: Cache) -> None:
    power = FakePower(failures=[httpx.ConnectError])
    with pytest.raises(SourceUnavailableError) as error:
        await make_client(power, cache).point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == NOT_ANSWERING_MESSAGE
    assert "simulated" not in str(error.value)
    assert len(power.requests) == 1


async def test_rejected_request_is_not_retried(cache: Cache) -> None:
    power = FakePower(failures=[422])
    with pytest.raises(SourceUnavailableError) as error:
        await make_client(power, cache).point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == REJECTED_MESSAGE
    assert len(power.requests) == 1


async def test_response_that_is_not_json_raises_source_unavailable(cache: Cache) -> None:
    client = make_client(lambda _: httpx.Response(200, text="<html>busy</html>"), cache)
    with pytest.raises(SourceUnavailableError) as error:
        await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == UNREADABLE_MESSAGE


async def test_response_without_a_requested_code_raises_source_unavailable(cache: Cache) -> None:
    client = make_client(lambda _: httpx.Response(200, json=point_payload(["T2M"])), cache)
    with pytest.raises(SourceUnavailableError) as error:
        await client.point_series(LAT, LON, ["T2M", "TS"], END_YEAR)
    assert error.value.message == UNREADABLE_MESSAGE


async def test_no_call_for_sixty_seconds_after_a_429(cache: Cache) -> None:
    clock, power = FakeClock(), FakePower(failures=[429])
    client = make_client(power, cache, clock=clock)
    with pytest.raises(SourceUnavailableError) as error:
        await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    assert error.value.message == PAUSED_MESSAGE

    clock.now = 59.9
    with pytest.raises(SourceUnavailableError):
        await client.point_series(LAT + 1, LON, ["T2M"], END_YEAR)
    assert len(power.requests) == 1

    clock.now = 60.0
    await client.point_series(LAT + 1, LON, ["T2M"], END_YEAR)
    assert len(power.requests) == 2


async def test_cached_request_still_answers_after_a_429(cache: Cache) -> None:
    power = FakePower()
    client = make_client(power, cache)
    expected = await client.point_series(LAT, LON, ["T2M"], END_YEAR)
    client = make_client(FakePower(failures=[429]), cache)
    with pytest.raises(SourceUnavailableError):
        await client.point_series(LAT + 1, LON, ["T2M"], END_YEAR)
    assert await client.point_series(LAT, LON, ["T2M"], END_YEAR) == expected


# Concurrency


async def test_at_most_two_calls_at_once(cache: Cache) -> None:
    power = GatedPower()
    client = make_client(power, cache)
    requests = [
        asyncio.create_task(client.point_series(LAT + step, LON, ["T2M"], END_YEAR))
        for step in range(4)
    ]
    await let_tasks_run()
    assert len(power.requests) == 2
    power.release()
    await asyncio.gather(*requests)
    assert len(power.requests) == 4
    assert power.most_open_calls == 2


async def test_concurrent_requests_for_one_grid_point_share_one_call(cache: Cache) -> None:
    power = GatedPower()
    client = make_client(power, cache)
    requests = [
        asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR)) for _ in range(3)
    ]
    await let_tasks_run()
    power.release()
    first, *others = await asyncio.gather(*requests)
    assert all(other == first for other in others)
    assert len(power.requests) == 1


async def test_concurrent_requests_for_other_codes_at_one_point_are_answered(
    cache: Cache,
) -> None:
    power = GatedPower()
    client = make_client(power, cache)
    air = asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR))
    await let_tasks_run()
    skin = asyncio.create_task(client.point_series(LAT, LON, ["T2M", "TS"], END_YEAR))
    await let_tasks_run()
    assert len(power.requests) == 1
    power.release()
    await air
    assert set(await skin) == {"T2M", "TS"}
    assert [codes_of(request) for request in power.requests] == [["T2M"], ["TS"]]


async def test_cancelling_the_request_that_started_a_shared_fetch_still_answers_the_other(
    cache: Cache,
) -> None:
    power = GatedPower()
    client = make_client(power, cache)
    starter = asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR))
    await let_tasks_run()
    joiner = asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR))
    await let_tasks_run()
    starter.cancel()
    await let_tasks_run()
    power.release()
    assert set(await joiner) == {"T2M"}
    assert len(power.requests) == 1


async def test_cancelling_a_request_that_joined_a_shared_fetch_still_answers_the_first(
    cache: Cache,
) -> None:
    power = GatedPower()
    client = make_client(power, cache)
    starter = asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR))
    await let_tasks_run()
    joiner = asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR))
    await let_tasks_run()
    joiner.cancel()
    await let_tasks_run()
    power.release()
    assert set(await starter) == {"T2M"}
    assert len(power.requests) == 1


async def test_fetch_failing_after_its_only_request_was_cancelled_is_not_reported(
    cache: Cache,
) -> None:
    gate = asyncio.Event()

    async def reject_when_released(_: httpx.Request) -> httpx.Response:
        await gate.wait()
        return httpx.Response(httpx.codes.BAD_REQUEST, text="simulated failure")

    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    reports: list[dict[str, Any]] = []
    loop.set_exception_handler(lambda _, context: reports.append(context))
    try:
        client = make_client(reject_when_released, cache)
        request = asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR))
        await let_tasks_run()
        request.cancel()
        await let_tasks_run()
        gate.set()
        await let_tasks_run()
        # asyncio reports a task exception nobody retrieved when the task is collected.
        del request
        gc.collect()
    finally:
        loop.set_exception_handler(previous_handler)
    assert reports == []


def test_request_arriving_as_a_fetch_finishes_gets_its_own_call(cache: Cache) -> None:
    power = FakePower()

    async def scenario() -> list[dict[str, PointSeries]]:
        client = make_client(power, cache)
        air = asyncio.create_task(client.point_series(LAT, LON, ["T2M"], END_YEAR))
        # After one step the air request has started its fetch. The fake POWER answers without
        # waiting, so that fetch finishes before the skin request takes its first step.
        await asyncio.sleep(0)
        skin = asyncio.create_task(client.point_series(LAT, LON, ["TS"], END_YEAR))
        return await asyncio.gather(air, skin)

    air, skin = run_with_time_limit(scenario())
    assert (set(air), set(skin)) == ({"T2M"}, {"TS"})
    assert [codes_of(request) for request in power.requests] == [["T2M"], ["TS"]]


# Regional calls

BOX = Box(south=55.0, west=20.0, north=65.0, east=30.0)
REGIONAL_END_YEAR = 2021


# Spec 6: POWER returns the grid points inside a box whose edges fall between grid lines. For
# this box it sent 320 cells, from 55.5 to 65.0 north and 20.625 to 30.0 east (13 Nov 2026).
BOX_BETWEEN_GRID_LINES = Box(south=55.2, west=20.3, north=65.2, east=30.3)
CELLS_IN_BOX_BETWEEN_GRID_LINES = 320


def regional_power(requests: list[httpx.Request], payload: Any = REGIONAL) -> Handler:
    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    return answer


def regional_with_values(code: str, change: Callable[[dict[str, float]], object]) -> Any:
    """The saved regional response, sent as `code`, with `change` applied to each cell's values."""
    features = [
        {
            **feature,
            "properties": {
                "parameter": {code: change(dict(feature["properties"]["parameter"]["T2M"]))}
            },
        }
        for feature in REGIONAL["features"]
    ]
    return {**REGIONAL, "features": features}


async def test_regional_call_asks_for_the_box_and_full_record(cache: Cache) -> None:
    requests: list[httpx.Request] = []
    await make_client(regional_power(requests), cache).regional_series(
        "T2M", BOX, REGIONAL_END_YEAR
    )
    (request,) = requests
    assert request.url.path == REGIONAL_PATH
    assert dict(request.url.params) == {
        "parameters": "T2M",
        "community": "AG",
        "latitude-min": "55.0",
        "latitude-max": "65.0",
        "longitude-min": "20.0",
        "longitude-max": "30.0",
        "start": "1981",
        "end": "2021",
        "format": "JSON",
    }


async def test_regional_series_parses_every_cell(cache: Cache) -> None:
    client = make_client(regional_power([]), cache)
    cells = await client.regional_series("T2M", BOX, REGIONAL_END_YEAR)
    assert len(cells) == len(REGIONAL["features"])
    helsinki = cells[(60.0, 25.0)]
    assert (helsinki.lat, helsinki.lon) == (60.0, 25.0)
    assert helsinki.monthly[(2020, 1)] == FULL["properties"]["parameter"]["T2M"]["202001"]
    assert len(helsinki.monthly) == 24
    assert (55.0, 20.625) in cells


async def test_regional_cells_are_cached_as_points(cache: Cache) -> None:
    requests: list[httpx.Request] = []
    client = make_client(regional_power(requests), cache)
    cells = await client.regional_series("T2M", BOX, REGIONAL_END_YEAR)
    point = await client.point_series(55.0, 20.625, ["T2M"], REGIONAL_END_YEAR)
    assert point["T2M"] == cells[(55.0, 20.625)]
    assert len(requests) == 1


async def test_regional_values_that_are_not_an_object_raise_source_unavailable(
    cache: Cache,
) -> None:
    payload = regional_with_values("T2M", lambda values: list(values.values()))
    client = make_client(regional_power([], payload), cache)
    with pytest.raises(SourceUnavailableError) as error:
        await client.regional_series("T2M", BOX, REGIONAL_END_YEAR)
    assert error.value.message == UNREADABLE_MESSAGE


async def test_regional_soil_wetness_that_is_one_in_every_month_becomes_missing(
    cache: Cache,
) -> None:
    payload = regional_with_values("GWETTOP", lambda values: dict.fromkeys(values, 1.0))
    client = make_client(regional_power([], payload), cache)
    cells = await client.regional_series("GWETTOP", BOX, REGIONAL_END_YEAR)
    assert len(cells) == len(REGIONAL["features"])
    assert {value for cell in cells.values() for value in cell.monthly.values()} == {None}


async def test_cached_box_is_answered_without_a_call(cache: Cache) -> None:
    expected = await make_client(regional_power([]), cache).regional_series(
        "T2M", BOX, REGIONAL_END_YEAR
    )
    requests: list[httpx.Request] = []
    client = make_client(regional_power(requests), cache)
    assert await client.regional_series("T2M", BOX, REGIONAL_END_YEAR) == expected
    assert requests == []


async def test_cached_box_is_still_answered_after_a_429(cache: Cache) -> None:
    expected = await make_client(regional_power([]), cache).regional_series(
        "T2M", BOX, REGIONAL_END_YEAR
    )
    power = FakePower(failures=[429])
    client = make_client(power, cache)
    with pytest.raises(SourceUnavailableError):
        await client.point_series(LAT, LON, ["TS"], END_YEAR)
    assert await client.regional_series("T2M", BOX, REGIONAL_END_YEAR) == expected
    assert len(power.requests) == 1


async def test_box_with_one_grid_point_not_cached_is_fetched(cache: Cache) -> None:
    all_but_first = {**REGIONAL, "features": REGIONAL["features"][1:]}
    await make_client(regional_power([], all_but_first), cache).regional_series(
        "T2M", BOX, REGIONAL_END_YEAR
    )
    requests: list[httpx.Request] = []
    client = make_client(regional_power(requests), cache)
    cells = await client.regional_series("T2M", BOX, REGIONAL_END_YEAR)
    assert len(cells) == len(REGIONAL["features"])
    assert len(requests) == 1


async def test_box_cached_to_an_earlier_year_is_fetched_again(cache: Cache) -> None:
    requests: list[httpx.Request] = []
    client = make_client(regional_power(requests), cache)
    await client.regional_series("T2M", BOX, REGIONAL_END_YEAR - 1)
    await client.regional_series("T2M", BOX, REGIONAL_END_YEAR)
    assert [request.url.params["end"] for request in requests] == ["2020", "2021"]


async def test_cached_box_between_grid_lines_holds_the_grid_points_inside(cache: Cache) -> None:
    await make_client(regional_power([]), cache).regional_series("T2M", BOX, REGIONAL_END_YEAR)
    requests: list[httpx.Request] = []
    client = make_client(regional_power(requests), cache)
    cells = await client.regional_series("T2M", BOX_BETWEEN_GRID_LINES, REGIONAL_END_YEAR)
    assert len(cells) == CELLS_IN_BOX_BETWEEN_GRID_LINES
    assert min(cells) == (55.5, 20.625)
    assert max(cells) == (65.0, 30.0)
    assert requests == []


# Spec 6: in a regional call, sunlight and cloud come back as 1° cells centred on half degrees.
ONE_DEGREE_BOX = Box(south=60.0, west=24.0, north=62.0, east=26.0)
ONE_DEGREE_CELLS = [(60.5, 24.5), (60.5, 25.5), (61.5, 24.5), (61.5, 25.5)]
# Every 0.5° of latitude and 0.625° of longitude inside the same box.
MERRA2_GRID_POINTS_IN_ONE_DEGREE_BOX = [
    (lat, lon) for lat in (60.0, 60.5, 61.0, 61.5, 62.0) for lon in (24.375, 25.0, 25.625)
]


def one_degree_regional(code: str) -> dict[str, Any]:
    """A regional response for `code` over ONE_DEGREE_BOX in 1° cells, with saved values."""
    values = REGIONAL["features"][0]["properties"]["parameter"]["T2M"]
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat, 0.0]},
            "properties": {"parameter": {code: values}},
        }
        for lat, lon in ONE_DEGREE_CELLS
    ]
    return {**REGIONAL, "features": features}


def test_codes_on_one_degree_grid_are_the_catalogue_codes_bounded_by_multiples() -> None:
    bounded = {
        entry.code
        for entry in load_catalogue()
        if entry.grid.alignment is GridAlignment.BOUNDED_BY_MULTIPLES
    }
    assert bounded == CODES_ON_ONE_DEGREE_GRID


@pytest.mark.parametrize("code", ["ALLSKY_SFC_SW_DWN", "CLOUD_AMT"])
async def test_one_degree_box_is_fetched_even_when_its_merra2_grid_points_are_cached(
    cache: Cache, code: str
) -> None:
    point_client = make_client(FakePower(), cache)
    for lat, lon in MERRA2_GRID_POINTS_IN_ONE_DEGREE_BOX:
        await point_client.point_series(lat, lon, [code], END_YEAR)
    requests: list[httpx.Request] = []
    client = make_client(regional_power(requests, one_degree_regional(code)), cache)
    cells = await client.regional_series(code, ONE_DEGREE_BOX, END_YEAR)
    assert sorted(cells) == ONE_DEGREE_CELLS
    assert len(requests) == 1


async def test_box_without_a_grid_point_inside_is_fetched(cache: Cache) -> None:
    requests: list[httpx.Request] = []
    client = make_client(regional_power(requests), cache)
    await client.regional_series(
        "T2M", Box(south=55.1, west=20.1, north=55.4, east=20.5), REGIONAL_END_YEAR
    )
    assert len(requests) == 1
