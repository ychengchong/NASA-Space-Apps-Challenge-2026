"""The only code that calls NASA POWER (spec 6). Everything else reads through the cache.

Every value leaves this module as a float or None: POWER's fill value (-999) becomes None here,
as does the constant soil wetness POWER sends over open ocean, and POWER's own annual values
(month 13) are dropped.
"""

import asyncio
import dataclasses
import math
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import date
from typing import Any

import httpx

from app.cache import Cache
from app.errors import SourceUnavailableError
from app.models import Box
from app.sources.base import MonthKey, PointSeries
from app.tools.places import GRID_LAT_STEP, GRID_LON_STEP

POWER_BASE_URL = "https://power.larc.nasa.gov"
POINT_PATH = "/api/temporal/monthly/point"
REGIONAL_PATH = "/api/temporal/monthly/regional"

# Cache rows carry their source, so this names POWER's rows.
CACHE_SOURCE = "power"

# Spec 6, "How the app calls it": every request uses this community and format.
COMMUNITY = "AG"
RESPONSE_FORMAT = "JSON"
# Spec 6, "Limits we observed": a start year of 1980 is rejected; 1981 is the earliest.
FIRST_YEAR = 1981
# Spec 6, "How the app calls it": a point call accepts up to 20 codes.
MAX_CODES_PER_CALL = 20
# Spec 6, "How the app calls it": a missing value is -999. The response header's fill_value
# is used when present.
DEFAULT_FILL_VALUE = -999.0
# Spec 6, "How the app calls it": each year also has a month 13, POWER's own annual value,
# which the app ignores.
ANNUAL_MONTH = 13
# Spec 6, "Limits we observed": over open ocean POWER sends GWETTOP as a constant 1.0 instead of
# its fill value (seen on 13 November 2026). A series of these codes that is exactly this value
# in every month it reports is treated as missing, so soil wetness over open ocean gives the
# no_data verdict.
CODES_SATURATED_OVER_OCEAN = frozenset({"GWETTOP"})
OCEAN_SATURATION_VALUE = 1.0
# Spec 6, "Limits we observed": these codes sit on 1° cells bounded by whole degrees and centred
# on half degrees, not on the MERRA-2 grid. A cached box is looked up by its MERRA-2 grid points,
# which are not these cells, so a box of either code is never answered from the cache.
CODES_ON_ONE_DEGREE_GRID = frozenset({"ALLSKY_SFC_SW_DWN", "CLOUD_AMT"})

# Spec 6, "How the app behaves toward POWER".
CALL_TIMEOUT_SECONDS = 20.0  # each call, from sending the request to reading the whole body
CALL_ATTEMPTS = 2  # a call is retried once, after a timeout or a 5xx answer
RETRY_DELAY_SECONDS = 2.0
RATE_LIMIT_PAUSE_SECONDS = 60.0  # no POWER call at all for this long after a 429
MAX_CONCURRENT_CALLS = 2

# Messages for SourceUnavailableError. They reach users, so they never carry raw error text.
NOT_ANSWERING_MESSAGE = "NASA POWER did not answer. Please try again in a few minutes."
PAUSED_MESSAGE = "NASA POWER asked the app to slow down. Please try again in a minute."
REJECTED_MESSAGE = "NASA POWER did not accept the request for this data."
UNREADABLE_MESSAGE = "NASA POWER sent a response the app could not read."

Clock = Callable[[], float]
Today = Callable[[], date]
Sleep = Callable[[float], Awaitable[None]]
PointKey = tuple[float, float, int]  # (lat, lon, end_year)


class PowerClient:
    """Reads POWER's monthly API through the cache. Implements `SeriesSource`.

    `clock` (seconds, monotonic), `today` and `sleep` are injected so tests control time.
    """

    def __init__(
        self,
        cache: Cache,
        http: httpx.AsyncClient | None = None,
        *,
        clock: Clock = time.monotonic,
        today: Today = date.today,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._cache = cache
        self._owns_http = http is None
        self._http = http if http is not None else httpx.AsyncClient()
        self._clock = clock
        self._today = today
        self._sleep = sleep
        self._calls = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
        self._paused_until = float("-inf")
        self._point_fetches: dict[PointKey, asyncio.Task[dict[str, PointSeries]]] = {}

    async def aclose(self) -> None:
        """Close the HTTP client if this object created it."""
        if self._owns_http:
            await self._http.aclose()

    async def point_series(
        self, lat: float, lon: float, codes: Sequence[str], end_year: int
    ) -> dict[str, PointSeries]:
        """The monthly record from 1981 to `end_year` of each code at one grid point.

        `lat` and `lon` must already be the centre of a cell of the codes' own grid, as
        `SeriesSource.point_series` says. Cached codes need no call; the others are
        fetched together, with their full record, and cached. Months after `end_year` are left
        out. Missing months are None. Raises `SourceUnavailableError` when a code is not cached
        and POWER cannot supply it.
        """
        wanted = list(dict.fromkeys(codes))
        found = self._cache.read_point_series(CACHE_SOURCE, lat, lon, wanted, end_year)
        key = (lat, lon, end_year)
        while missing := [code for code in wanted if code not in found]:
            running = self._point_fetches.get(key)
            if running is None:
                # This fetch asks for every missing code and raises unless POWER sends them all,
                # so the loop ends after it.
                found.update(await self._start_point_fetch(key, missing))
            else:
                # Spec 6: two requests for the same grid point at the same moment share one
                # call. The running fetch may cover other codes, so the loop checks again
                # afterwards. It has not finished, so waiting for it yields to the event loop.
                fetched = await asyncio.shield(running)
                found.update({code: fetched[code] for code in missing if code in fetched})
        return {code: _up_to(found[code], end_year) for code in wanted}

    async def regional_series(
        self, code: str, box: Box, end_year: int
    ) -> dict[tuple[float, float], PointSeries]:
        """The monthly record from 1981 to `end_year` of one code at every grid point in `box`.

        Keyed by (lat, lon) as POWER reports the grid points. When `code` is on the MERRA-2 grid
        and every grid point in the box is cached for it up to `end_year`, the box needs no
        call. Otherwise POWER is asked, and every cell is cached as a point, so opening one
        later needs no call. Months after `end_year` are left out. Missing months are None.
        Raises `SourceUnavailableError` when the box is not answered from the cache and POWER
        cannot supply it.
        """
        cached = self._cached_box(code, box, end_year)
        if cached is not None:
            return cached
        payload = await self._get_json(
            REGIONAL_PATH,
            {
                "parameters": code,
                "community": COMMUNITY,
                "latitude-min": box.south,
                "latitude-max": box.north,
                "longitude-min": box.west,
                "longitude-max": box.east,
                "start": FIRST_YEAR,
                "end": end_year,
                "format": RESPONSE_FORMAT,
            },
        )
        cells = _parse_regional(payload, code, self._accessed())
        self._cache.write_point_series(CACHE_SOURCE, cells.values(), end_year)
        return cells

    async def _start_point_fetch(self, key: PointKey, codes: list[str]) -> dict[str, PointSeries]:
        """Fetch `codes` at one grid point as a task that other requests for the point can join."""
        fetch = asyncio.create_task(self._fetch_point(key, codes))
        fetch.add_done_callback(_retrieve_outcome)
        self._point_fetches[key] = fetch
        # Shielded, so one caller giving up does not cancel the fetch the others wait for.
        return await asyncio.shield(fetch)

    async def _fetch_point(self, key: PointKey, codes: list[str]) -> dict[str, PointSeries]:
        lat, lon, end_year = key
        try:
            fetched: dict[str, PointSeries] = {}
            for start in range(0, len(codes), MAX_CODES_PER_CALL):
                batch = codes[start : start + MAX_CODES_PER_CALL]
                payload = await self._get_json(
                    POINT_PATH,
                    {
                        "parameters": ",".join(batch),
                        "community": COMMUNITY,
                        "latitude": lat,
                        "longitude": lon,
                        "start": FIRST_YEAR,
                        "end": end_year,
                        "format": RESPONSE_FORMAT,
                    },
                )
                series = _parse_point(payload, batch, lat, lon, self._accessed())
                self._cache.write_point_series(CACHE_SOURCE, series.values(), end_year)
                fetched.update(series)
            return fetched
        finally:
            # Removed here rather than in a done callback, which runs a loop step later: a
            # request must never join a finished fetch, or point_series would loop on it
            # without ever yielding to the event loop.
            self._point_fetches.pop(key, None)

    def _cached_box(
        self, code: str, box: Box, end_year: int
    ) -> dict[tuple[float, float], PointSeries] | None:
        """Every MERRA-2 grid point of `box` from the cache.

        None when any of them is not cached, or when `code` is not on the MERRA-2 grid.
        """
        if code in CODES_ON_ONE_DEGREE_GRID:
            return None
        grid_points = _grid_points(box)
        if not grid_points:
            return None
        cells: dict[tuple[float, float], PointSeries] = {}
        for lat, lon in grid_points:
            cached = self._cache.read_point_series(CACHE_SOURCE, lat, lon, [code], end_year)
            if code not in cached:
                return None
            cells[(lat, lon)] = _up_to(cached[code], end_year)
        return cells

    async def _get_json(self, path: str, params: Mapping[str, str | int | float]) -> Any:
        """One POWER call, retried once after a timeout or a 5xx answer, parsed as JSON."""
        for attempt in range(CALL_ATTEMPTS):
            if attempt > 0:
                await self._sleep(RETRY_DELAY_SECONDS)
            response = await self._attempt(path, params)
            if response is None:
                continue
            try:
                return response.json()
            except ValueError as error:
                raise SourceUnavailableError(UNREADABLE_MESSAGE) from error
        raise SourceUnavailableError(NOT_ANSWERING_MESSAGE)

    async def _attempt(
        self, path: str, params: Mapping[str, str | int | float]
    ) -> httpx.Response | None:
        """Send one request. Returns None after a timeout or a 5xx answer, which may be retried."""
        async with self._calls:
            if self._clock() < self._paused_until:
                raise SourceUnavailableError(PAUSED_MESSAGE)
            try:
                # httpx's own timeouts apply to each phase and default to 5 s, so they are
                # raised to the limit and the whole call is bounded by asyncio.timeout.
                async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
                    response = await self._http.get(
                        POWER_BASE_URL + path, params=params, timeout=CALL_TIMEOUT_SECONDS
                    )
            except (httpx.TimeoutException, TimeoutError):
                return None
            except httpx.HTTPError as error:
                raise SourceUnavailableError(NOT_ANSWERING_MESSAGE) from error
        if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            self._paused_until = self._clock() + RATE_LIMIT_PAUSE_SECONDS
            raise SourceUnavailableError(PAUSED_MESSAGE)
        if response.is_server_error:
            return None
        if not response.is_success:
            raise SourceUnavailableError(REJECTED_MESSAGE)
        return response

    def _accessed(self) -> str:
        return self._today().isoformat()


def _retrieve_outcome(fetch: asyncio.Task[dict[str, PointSeries]]) -> None:
    """Mark a finished point fetch's error as seen.

    Requests still waiting for the fetch get its result or error through the shield. When every
    one of them was cancelled, asyncio would otherwise log the error with a traceback, and spec
    11 keeps logs to the method, path, status and duration.
    """
    if not fetch.cancelled():
        fetch.exception()


def parse_monthly(values: object, fill_value: float) -> dict[MonthKey, float | None]:
    """Turn POWER's {"YYYYMM": value} into {(year, month): value}.

    Months equal to `fill_value` (or null) become None; month 13 keys are dropped. Raises
    TypeError when `values` is not a JSON object, and ValueError on a key that is not a year
    and a month.
    """
    if not isinstance(values, Mapping):
        raise TypeError("the monthly values are not a JSON object")
    monthly: dict[MonthKey, float | None] = {}
    for key, value in values.items():
        year, month = _month_key(key)
        if month == ANNUAL_MONTH:
            continue
        monthly[(year, month)] = None if value is None or value == fill_value else float(value)
    return monthly


def _month_key(key: str) -> MonthKey:
    """(year, month) from a "YYYYMM" key; month 13 is POWER's annual value."""
    if len(key) != len("YYYYMM") or not key.isdigit():
        raise ValueError(f"not a POWER month key: {key!r}")
    year, month = int(key[:4]), int(key[4:])
    if not 1 <= month <= ANNUAL_MONTH:
        raise ValueError(f"not a POWER month key: {key!r}")
    return year, month


def _parse_code(code: str, values: object, fill_value: float) -> dict[MonthKey, float | None]:
    """`parse_monthly` for one code, with the open-ocean soil wetness turned into None."""
    monthly = parse_monthly(values, fill_value)
    if code in CODES_SATURATED_OVER_OCEAN and _is_ocean_saturation(monthly):
        return dict.fromkeys(monthly, None)
    return monthly


def _is_ocean_saturation(monthly: Mapping[MonthKey, float | None]) -> bool:
    """True when at least one month has a value and every such value is the ocean's 1.0."""
    reported = [value for value in monthly.values() if value is not None]
    return bool(reported) and all(value == OCEAN_SATURATION_VALUE for value in reported)


def _parse_point(
    payload: Any, codes: Sequence[str], lat: float, lon: float, accessed: str
) -> dict[str, PointSeries]:
    try:
        version, fill_value = _header(payload)
        parameter = payload["properties"]["parameter"]
        return {
            code: PointSeries(
                code=code,
                lat=lat,
                lon=lon,
                monthly=_parse_code(code, parameter[code], fill_value),
                version=version,
                accessed=accessed,
            )
            for code in codes
        }
    except (KeyError, TypeError, ValueError) as error:
        raise SourceUnavailableError(UNREADABLE_MESSAGE) from error


def _parse_regional(
    payload: Any, code: str, accessed: str
) -> dict[tuple[float, float], PointSeries]:
    try:
        version, fill_value = _header(payload)
        cells: dict[tuple[float, float], PointSeries] = {}
        for feature in payload["features"]:
            lon, lat = (float(value) for value in feature["geometry"]["coordinates"][:2])
            cells[(lat, lon)] = PointSeries(
                code=code,
                lat=lat,
                lon=lon,
                monthly=_parse_code(code, feature["properties"]["parameter"][code], fill_value),
                version=version,
                accessed=accessed,
            )
        return cells
    except (KeyError, TypeError, ValueError) as error:
        raise SourceUnavailableError(UNREADABLE_MESSAGE) from error


def _header(payload: Any) -> tuple[str, float]:
    """The API version and the fill value from a response header."""
    header = payload["header"]
    version = header["api"]["version"]
    if not isinstance(version, str):
        raise TypeError("the API version is not text")
    return version, float(header.get("fill_value", DEFAULT_FILL_VALUE))


def _grid_points(box: Box) -> list[tuple[float, float]]:
    """The grid points a regional call returns for `box`, as (lat, lon), in POWER's order.

    Spec 6, "Places and grid cells": the points sit on multiples of the grid steps. POWER
    returns every such point inside the box, edges included (checked 13 November 2026 with box
    edges on and between grid lines), listed south to north, then west to east.
    """
    lats = _multiples_between(box.south, box.north, GRID_LAT_STEP)
    lons = _multiples_between(box.west, box.east, GRID_LON_STEP)
    return [(lat, lon) for lat in lats for lon in lons]


def _multiples_between(low: float, high: float, step: float) -> list[float]:
    return [index * step for index in range(math.ceil(low / step), math.floor(high / step) + 1)]


def _up_to(series: PointSeries, end_year: int) -> PointSeries:
    monthly = {key: value for key, value in series.monthly.items() if key[0] <= end_year}
    return dataclasses.replace(series, monthly=monthly)
