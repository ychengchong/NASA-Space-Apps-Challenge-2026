"""What the tool layer needs from a data source. Only `sources/` knows where the data comes from."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.models import Box

# A month is (year, month) with month 1 to 12. A missing value is None, never -999 or zero.
MonthKey = tuple[int, int]
MonthlyValues = Mapping[MonthKey, float | None]


@dataclass(frozen=True)
class PointSeries:
    """The full monthly record of one code at one grid point."""

    code: str
    lat: float
    lon: float
    monthly: MonthlyValues
    version: str  # API version reported by the source, such as "v2.10.0"
    accessed: str  # date the values were fetched from the source, "YYYY-MM-DD"


class SeriesSource(Protocol):
    async def point_series(
        self, lat: float, lon: float, codes: Sequence[str], end_year: int
    ) -> dict[str, PointSeries]:
        """Monthly values from the earliest year up to `end_year` for each code at a grid point.

        `lat` and `lon` are the exact centre of a cell of the codes' own grid: a MERRA-2 grid
        point, or the centre of a 1° cell for sunlight and cloud. Raises
        `SourceUnavailableError` when the source cannot answer and the data is not cached.
        """
        ...

    async def regional_series(
        self, code: str, box: Box, end_year: int
    ) -> dict[tuple[float, float], PointSeries]:
        """Monthly values for every grid point in a box, keyed by (lat, lon)."""
        ...
