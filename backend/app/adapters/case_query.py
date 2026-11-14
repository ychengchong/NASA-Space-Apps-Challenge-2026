"""Turns the case and map parameters of spec 10 into tool inputs. Translation only, no analysis.

The REST adapter reads them from the query string and the chat adapter from the `case` field.
"""

import math
from collections.abc import Mapping, Sequence
from typing import get_args
from urllib.parse import parse_qs

from pydantic import ValidationError

from app.errors import BadPlaceError, BadRequestError
from app.models import (
    MAX_COMPARE_PLACES,
    PLACE_NAME_MAX_LENGTH,
    AnalyzeTrendInput,
    Box,
    ComparePlacesInput,
    MapTrendsInput,
    PlaceInput,
    Season,
)

# Parameter name -> every value given for it, in order, as `parse_qs` returns them.
QueryValues = Mapping[str, Sequence[str]]

SEASONS: tuple[str, ...] = get_args(Season)
SCAN_ON = "1"
SCAN_OFF = "0"


def parse_query_string(text: str) -> dict[str, list[str]]:
    """Split a query string such as "v=air_temp&p=60.17,24.94" into its parameters."""
    return parse_qs(text.lstrip("?"), keep_blank_values=True)


def parse_case_query(query: QueryValues) -> AnalyzeTrendInput | ComparePlacesInput:
    """The tool input for a case: `analyze_trend` for one place, `compare_places` for two to four.

    Raises `BadPlaceError` for missing, malformed or too many places, and `BadRequestError` for
    any other invalid parameter. An unknown variable is left for the tool to report.
    """
    variable = _required_single(query, "v")
    places = _places(query)
    period = _period(query)
    scan = _scan(query)
    try:
        if len(places) == 1:
            return AnalyzeTrendInput.model_validate(
                {"variable": variable, "place": places[0], "scan": scan, **period}
            )
        return ComparePlacesInput.model_validate(
            {"variable": variable, "places": places, "scan": scan, **period}
        )
    except ValidationError as error:
        raise BadRequestError("The case parameters are not valid.") from error


def parse_map_query(query: QueryValues) -> MapTrendsInput:
    """The tool input for a trend map. Raises `BadPlaceError` or `BadRequestError`."""
    variable = _required_single(query, "v")
    box = _box(_required_single(query, "box"))
    period = _period(query)
    try:
        return MapTrendsInput.model_validate({"variable": variable, "box": box, **period})
    except ValidationError as error:
        raise BadRequestError("The map parameters are not valid.") from error


def _single(query: QueryValues, name: str) -> str | None:
    values = query.get(name, [])
    if len(values) > 1:
        raise BadRequestError(f"Give '{name}' only once.")
    return values[0] if values else None


def _required_single(query: QueryValues, name: str) -> str:
    value = _single(query, name)
    if value is None or value.strip() == "":
        raise BadRequestError(f"The parameter '{name}' is missing.")
    return value.strip()


def _places(query: QueryValues) -> list[PlaceInput]:
    points = list(query.get("p", []))
    if not points:
        raise BadPlaceError("Give at least one place as p=latitude,longitude.")
    if len(points) > MAX_COMPARE_PLACES:
        raise BadPlaceError(f"A case can hold at most {MAX_COMPARE_PLACES} places.")
    labels = _labels(query, len(points))
    return [
        PlaceInput(lat=lat, lon=lon, name=label)
        for (lat, lon), label in zip((_point(text) for text in points), labels, strict=True)
    ]


def _labels(query: QueryValues, n_places: int) -> list[str | None]:
    labels = list(query.get("label", []))
    if not labels:
        return [None] * n_places
    if len(labels) != n_places:
        raise BadRequestError("Give one label per place, in the same order, or none at all.")
    cleaned: list[str | None] = []
    for label in labels:
        text = label.strip()
        if len(text) > PLACE_NAME_MAX_LENGTH:
            raise BadRequestError(
                f"A place label can be at most {PLACE_NAME_MAX_LENGTH} characters long."
            )
        cleaned.append(text or None)
    return cleaned


def _point(text: str) -> tuple[float, float]:
    parts = text.split(",")
    if len(parts) != 2:
        raise BadPlaceError("Give each place as p=latitude,longitude.")
    lat, lon = (_number(part, BadPlaceError) for part in parts)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise BadPlaceError("Latitude must be from -90 to 90 and longitude from -180 to 180.")
    return lat, lon


def _box(text: str) -> Box:
    parts = text.split(",")
    if len(parts) != 4:
        raise BadPlaceError("Give the box as box=south,west,north,east.")
    south, west, north, east = (_number(part, BadPlaceError) for part in parts)
    try:
        return Box(south=south, west=west, north=north, east=east)
    except ValidationError as error:
        raise BadPlaceError(
            "Box latitudes must be from -90 to 90 and longitudes from -180 to 180."
        ) from error


def _number(text: str, error: type[BadPlaceError] | type[BadRequestError]) -> float:
    try:
        value = float(text.strip())
    except ValueError:
        raise error(f"'{text.strip()}' is not a number.") from None
    if not math.isfinite(value):
        raise error(f"'{text.strip()}' is not a number.")
    return value


def _period(query: QueryValues) -> dict[str, int | str]:
    period: dict[str, int | str] = {}
    for name in ("from", "to"):
        value = _single(query, name)
        if value is not None and value.strip() != "":
            period[name] = _year(name, value)
    season = _single(query, "s")
    if season is not None and season.strip() != "":
        if season.strip() not in SEASONS:
            raise BadRequestError(f"The season must be one of {', '.join(SEASONS)}.")
        period["season"] = season.strip()
    return period


def _year(name: str, text: str) -> int:
    try:
        return int(text.strip())
    except ValueError:
        raise BadRequestError(f"'{name}' must be a whole year, such as 1981.") from None


def _scan(query: QueryValues) -> bool:
    value = _single(query, "scan")
    if value is None or value.strip() in ("", SCAN_OFF):
        return False
    if value.strip() == SCAN_ON:
        return True
    raise BadRequestError("Set 'scan' to 1 to include the period scan.")
