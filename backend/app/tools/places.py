"""find_place and the grid helpers (spec 5, "How the two search tools match"; spec 6, "Places
and grid cells"; spec 11, "Security and privacy").
"""

import json
import math
import unicodedata
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.catalogue import CatalogueEntry, GridAlignment, GridSize
from app.config import DATA_DIR
from app.models import Cell, FindPlaceInput, Place, PlaceCandidate, PlaceInput

PLACES_PATH = DATA_DIR / "places.json"

# Spec 5: find_place returns five matches at most.
MAX_PLACE_CANDIDATES = 5
# Spec 6: MERRA-2 grid points sit every 0.5° of latitude and every 0.625° of longitude. The
# variables on this grid snap to it, so one cached POWER call serves all their codes at a point.
GRID_LAT_STEP = 0.5
GRID_LON_STEP = 0.625
MAX_LATITUDE = 90.0
FULL_CIRCLE = 360.0
HALF_CIRCLE = 180.0
# Spec 5: an unnamed place is labelled with the centre of its cell, such as "60.0°N, 25.0°E".
NAME_COORDINATE_DECIMALS = 1
# Spec 11: coordinates in a link are rounded to two decimals.
LINK_COORDINATE_DECIMALS = 2


class PlaceRecord(BaseModel):
    """One entry of places.json, including fields that never leave the server, like `population`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    alt_names: tuple[str, ...] = ()
    country: str | None = None
    lat: float
    lon: float
    population: int = 0  # regions have none, so they rank after every matching city
    kind: Literal["city", "region"]
    region_type: str | None = None
    hand_picked: bool = False


class PlacesFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attribution: str
    places: tuple[PlaceRecord, ...]


class _NameMatch(IntEnum):
    """How closely a place's best name matches the query; a lower value ranks first."""

    EXACT = 0
    STARTS_WITH = 1
    CONTAINS = 2


@lru_cache(maxsize=4)
def load_places(path: Path = PLACES_PATH) -> tuple[PlaceRecord, ...]:
    """Every place in `path` (by default the bundled places.json), in the file's order.

    The file is read and validated once per path. Raises OSError when it cannot be read,
    json.JSONDecodeError when it is not JSON, and pydantic.ValidationError when it does not
    match `PlacesFile`.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PlacesFile.model_validate(raw).places


def _normalise(text: str) -> str:
    """`text` without accents, in lower case, with runs of whitespace collapsed to one space."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.casefold().split())


@lru_cache(maxsize=1)
def _search_index() -> tuple[tuple[PlaceRecord, tuple[str, ...]], ...]:
    """Every place with its name and alternative names normalised once."""
    return tuple(
        (record, tuple(_normalise(name) for name in (record.name, *record.alt_names)))
        for record in load_places()
    )


def _to_candidate(record: PlaceRecord) -> PlaceCandidate:
    return PlaceCandidate(
        name=record.name,
        country=record.country,
        lat=record.lat,
        lon=record.lon,
        kind=record.kind,
        region_type=record.region_type,
    )


def _name_match(query: str, names: tuple[str, ...]) -> _NameMatch | None:
    """The closest match between `query` and any of `names`, or None when none contains it."""
    if query in names:
        return _NameMatch.EXACT
    if any(name.startswith(query) for name in names):
        return _NameMatch.STARTS_WITH
    if any(query in name for name in names):
        return _NameMatch.CONTAINS
    return None


def find_place(inp: FindPlaceInput) -> list[PlaceCandidate]:
    """Up to five places whose name or an alternative name contains the query, best match first.

    Places whose name or an alternative name equals the query come first, then those with a
    name that starts with it, then the other matches, so "Sahara" finds the desert before the
    larger city of Sahāranpur. Within each group the most populous place comes first; regions
    count as population 0, and places of equal population keep the order of places.json.
    Matching ignores case and accents, so "sao paulo" finds "São Paulo". A query that matches
    nothing, or holds only whitespace, returns an empty list.
    """
    query = _normalise(inp.query)
    if not query:
        return []
    matches: list[tuple[_NameMatch, PlaceRecord]] = []
    for record, names in _search_index():
        match = _name_match(query, names)
        if match is not None:
            matches.append((match, record))
    # list.sort is stable, so places that tie keep the file's order.
    matches.sort(key=lambda found: (found[0], -found[1].population))
    return [_to_candidate(record) for _, record in matches[:MAX_PLACE_CANDIDATES]]


def _nearest_multiple(value: float, step: float) -> float:
    """The multiple of `step` nearest to `value`; a value exactly halfway goes up."""
    return math.floor(value / step + 0.5) * step


def _multiple_at_or_below(value: float, step: float) -> float:
    """The largest multiple of `step` that is not above `value`."""
    return math.floor(value / step) * step


def _wrap_longitude(lon: float) -> float:
    """`lon` in -180 (included) to 180 (excluded), so 180 becomes -180, the same meridian."""
    return (lon + HALF_CIRCLE) % FULL_CIRCLE - HALF_CIRCLE


def snap_to_grid(lat: float, lon: float) -> tuple[float, float]:
    """The MERRA-2 grid point nearest to (lat, lon), as (latitude, longitude) in degrees.

    A point exactly halfway between grid lines goes north or east. The latitude stays within
    -90 to 90. The longitude wraps into -180 (included) to 180 (excluded), so 179.9 becomes -180.0.
    """
    grid_lat = min(max(_nearest_multiple(lat, GRID_LAT_STEP), -MAX_LATITUDE), MAX_LATITUDE)
    grid_lon = _wrap_longitude(_nearest_multiple(lon, GRID_LON_STEP))
    return grid_lat, grid_lon


def _cell_centre(lat: float, lon: float, grid: GridSize) -> tuple[float, float]:
    """The centre of the cell of `grid` that holds (lat, lon), as (latitude, longitude) in degrees.

    On the MERRA-2 grid, the one grid centred on multiples, this is the nearest grid point, as
    `snap_to_grid` gives it. On a grid bounded by multiples, such as the 1° grid of sunlight and
    cloud, it is the centre of the cell from the multiple at or below each coordinate to the
    next, so a point on an edge takes the cell north or east of it, as POWER does (spec 6,
    "Limits we observed"). Its latitude is at most half a cell below 90°, so a point at the pole
    takes the cell south of it, and its longitude wraps as in `snap_to_grid`.
    """
    if grid.alignment is GridAlignment.CENTRED_ON_MULTIPLES:
        return snap_to_grid(lat, lon)
    half_height = grid.height / 2
    centre_lat = min(
        _multiple_at_or_below(lat, grid.height) + half_height, MAX_LATITUDE - half_height
    )
    centre_lon = _wrap_longitude(_multiple_at_or_below(lon, grid.width) + grid.width / 2)
    return centre_lat, centre_lon


def _format_degrees(value: float, positive: str, negative: str) -> str:
    text = f"{abs(value):.{NAME_COORDINATE_DECIMALS}f}"
    # A value that rounds to zero is written 0.0°N or 0.0°E, never 0.0°S or 0.0°W.
    is_negative = value < 0 and float(text) != 0
    return f"{text}°{negative if is_negative else positive}"


def format_coordinates(lat: float, lon: float) -> str:
    """Coordinates as text with one decimal, such as "60.0°N, 25.0°E" or "34.0°S, 58.1°W"."""
    return f"{_format_degrees(lat, 'N', 'S')}, {_format_degrees(lon, 'E', 'W')}"


def resolve_place(place: PlaceInput, entry: CatalogueEntry) -> Place:
    """The place as the tools report it: the requested point and the grid cell analysed.

    The cell is from the variable's own grid, resolved from the original coordinates
    before serializing a
    link: for a MERRA-2 variable the cell of the nearest grid point, and for sunlight and cloud
    the 1° cell bounded by whole degrees (spec 6). The cell's `lat` and `lon` are its centre,
    the point the source is asked for, and its size is the grid's. The name is the given name,
    or the centre's coordinates when no name is given. `lat` and `lon` stay as requested.
    """
    # Preserve the original coordinate when selecting the cell, including near boundaries.
    centre_lat, centre_lon = _cell_centre(place.lat, place.lon, entry.grid)
    given_name = place.name.strip() if place.name else ""
    return Place(
        name=given_name or format_coordinates(centre_lat, centre_lon),
        lat=place.lat,
        lon=place.lon,
        cell=Cell(lat=centre_lat, lon=centre_lon, height=entry.grid.height, width=entry.grid.width),
    )


def round_link_coordinate(x: float) -> float:
    """Retain coordinate precision for shared links; normalize only signed zero."""
    return x if x != 0 else 0.0
