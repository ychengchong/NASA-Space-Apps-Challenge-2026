"""A SeriesSource for tool tests: fixed monthly values per grid point, no network."""

import asyncio
from collections.abc import Mapping, Sequence

from app.models import Box
from app.sources.base import MonthKey, MonthlyValues, PointSeries

FAKE_VERSION = "v2.10.0"
FAKE_ACCESSED = "2026-11-13"
FIRST_RECORD_YEAR = 1981

GridPoint = tuple[float, float]


def monthly_from_yearly(yearly: Mapping[int, float | None]) -> dict[MonthKey, float | None]:
    """Every month of each year set to that year's value, so each season's mean equals it."""
    return {(year, month): value for year, value in yearly.items() for month in range(1, 13)}


def line(
    slope_per_year: float, first_year: int = FIRST_RECORD_YEAR, last_year: int = 2025
) -> dict[int, float]:
    """Yearly values on an exact straight line, starting from 10.0 in `first_year`."""
    return {
        year: 10.0 + slope_per_year * (year - first_year)
        for year in range(first_year, last_year + 1)
    }


class FakeSource:
    """Serves a series for every code it is asked for, at every grid point.

    A code's values are `by_code[code]` where one is given, else `by_point[(lat, lon)]` where one
    is given, else `monthly`. Records each point request as (lat, lon, codes, end_year). Months
    after `end_year` are left out, as the real client does.
    """

    def __init__(
        self,
        monthly: MonthlyValues | None = None,
        by_point: Mapping[GridPoint, MonthlyValues] | None = None,
        accessed: str = FAKE_ACCESSED,
        by_code: Mapping[str, MonthlyValues] | None = None,
    ) -> None:
        self.calls: list[tuple[float, float, tuple[str, ...], int]] = []
        self._monthly = monthly or {}
        self._by_point = by_point or {}
        self._by_code = by_code or {}
        self._accessed = accessed

    async def point_series(
        self, lat: float, lon: float, codes: Sequence[str], end_year: int
    ) -> dict[str, PointSeries]:
        self.calls.append((lat, lon, tuple(codes), end_year))
        point_monthly = self._by_point.get((lat, lon), self._monthly)
        return {
            code: PointSeries(
                code=code,
                lat=lat,
                lon=lon,
                monthly=_up_to(self._by_code.get(code, point_monthly), end_year),
                version=FAKE_VERSION,
                accessed=self._accessed,
            )
            for code in codes
        }

    async def regional_series(
        self, code: str, box: Box, end_year: int
    ) -> dict[GridPoint, PointSeries]:
        raise NotImplementedError("FakeSource serves grid points only")


class RegionalFakeSource(FakeSource):
    """Serves the same grid cells for every box, so a map test chooses its cells directly.

    `cells` maps each grid point (lat, lon) to its monthly values; they are returned in the
    order given. Records each regional request as (code, box, end_year). Months after
    `end_year` are left out, as the real client does. Point requests behave as in FakeSource.
    """

    def __init__(
        self, cells: Mapping[GridPoint, MonthlyValues], accessed: str = FAKE_ACCESSED
    ) -> None:
        super().__init__(accessed=accessed)
        self.regional_calls: list[tuple[str, Box, int]] = []
        self._cells = cells

    async def regional_series(
        self, code: str, box: Box, end_year: int
    ) -> dict[GridPoint, PointSeries]:
        self.regional_calls.append((code, box, end_year))
        return {
            (lat, lon): PointSeries(
                code=code,
                lat=lat,
                lon=lon,
                monthly=_up_to(monthly, end_year),
                version=FAKE_VERSION,
                accessed=self._accessed,
            )
            for (lat, lon), monthly in self._cells.items()
        }


class GatedSource(FakeSource):
    """Holds every request until `expected` requests are open at once.

    A caller that fetches one place after another never gets there, and times out.
    """

    def __init__(self, expected: int, monthly: MonthlyValues) -> None:
        super().__init__(monthly)
        self._expected = expected
        self._all_open = asyncio.Event()

    async def point_series(
        self, lat: float, lon: float, codes: Sequence[str], end_year: int
    ) -> dict[str, PointSeries]:
        answer = await super().point_series(lat, lon, codes, end_year)
        if len(self.calls) >= self._expected:
            self._all_open.set()
        await self._all_open.wait()
        return answer


def _up_to(monthly: MonthlyValues, end_year: int) -> dict[MonthKey, float | None]:
    return {key: value for key, value in monthly.items() if key[0] <= end_year}
