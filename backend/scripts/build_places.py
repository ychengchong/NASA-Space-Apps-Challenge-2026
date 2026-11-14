"""Build data/places.json, the list that find_place searches (spec 6, "Places and grid cells").

The list holds every GeoNames city of 100,000 people or more, plus about twenty natural regions
picked by hand. Download cities15000.zip and countryInfo.txt from
https://download.geonames.org/export/dump/ into an empty directory, then run from backend/:

    uv run python -I scripts/build_places.py --downloaded YYYY-MM-DD CITIES_ZIP COUNTRY_INFO

The script uses the standard library only, so it runs under `python -I`.
"""

import argparse
import json
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "places.json"
CITIES_MEMBER = "cities15000.txt"

# Spec 6 (decided with the team): cities of 100,000 people or more.
MIN_CITY_POPULATION = 100_000
# A city of this many people or more gets the region type "megacity".
MEGACITY_POPULATION = 10_000_000
# Four decimals is about 11 m, far finer than a grid cell of about 50 km.
COORDINATE_DECIMALS = 4
# GeoNames feature codes for places that are no longer cities: historical, abandoned, destroyed.
EXCLUDED_FEATURE_CODES = frozenset({"PPLH", "PPLQ", "PPLW"})

# Columns of the GeoNames "geoname" table, as listed in the export's readme.txt.
GEONAMES_COLUMNS = 19
NAME_COLUMN = 1
ASCII_NAME_COLUMN = 2
LATITUDE_COLUMN = 4
LONGITUDE_COLUMN = 5
FEATURE_CODE_COLUMN = 7
COUNTRY_CODE_COLUMN = 8
POPULATION_COLUMN = 14
# Columns of countryInfo.txt.
COUNTRY_INFO_CODE_COLUMN = 0
COUNTRY_INFO_NAME_COLUMN = 4

# Hand-picked natural regions, chosen with an AI coding assistant. Each point is a representative
# spot inside the region, not a boundary: on land, or at sea for an ocean region. A country is
# named only when the whole region lies in that one country.
REGIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "Sahara",
        "alt_names": ["Sahara Desert"],
        "lat": 23.0,
        "lon": 12.0,
        "region_type": "desert",
    },
    {
        "name": "Amazon rainforest",
        "alt_names": ["Amazonia", "Amazon Basin"],
        "lat": -5.0,
        "lon": -63.0,
        "region_type": "rainforest",
    },
    {
        "name": "Congo rainforest",
        "alt_names": ["Congo Basin"],
        "lat": 0.0,
        "lon": 22.0,
        "region_type": "rainforest",
    },
    {"name": "Sahel", "lat": 14.5, "lon": 5.0, "region_type": "savanna"},
    {
        "name": "Ganges Delta",
        "alt_names": ["Ganges-Brahmaputra Delta", "Bengal Delta"],
        "lat": 22.5,
        "lon": 89.5,
        "region_type": "delta",
    },
    {
        "name": "Greenland ice sheet",
        "alt_names": ["Greenland Ice Cap"],
        "country": "Greenland",
        "lat": 72.6,
        "lon": -38.5,
        "region_type": "ice sheet",
    },
    {
        "name": "Siberian tundra",
        "country": "Russia",
        "lat": 71.0,
        "lon": 90.0,
        "region_type": "tundra",
    },
    {
        "name": "Atacama Desert",
        "country": "Chile",
        "lat": -24.0,
        "lon": -69.5,
        "region_type": "desert",
    },
    {"name": "Great Plains", "lat": 39.0, "lon": -100.0, "region_type": "grassland"},
    {
        "name": "Mekong Delta",
        "country": "Vietnam",
        "lat": 10.0,
        "lon": 105.7,
        "region_type": "delta",
    },
    {
        "name": "Tibetan Plateau",
        "alt_names": ["Qinghai-Tibet Plateau"],
        "lat": 32.5,
        "lon": 88.0,
        "region_type": "plateau",
    },
    {
        "name": "Australian Outback",
        "country": "Australia",
        "lat": -25.0,
        "lon": 133.0,
        "region_type": "desert",
    },
    {"name": "Gobi Desert", "lat": 43.0, "lon": 105.0, "region_type": "desert"},
    {
        "name": "Arabian Desert",
        "alt_names": ["Rub' al Khali", "Empty Quarter"],
        "lat": 20.0,
        "lon": 50.0,
        "region_type": "desert",
    },
    {"name": "Borneo rainforest", "lat": 0.5, "lon": 114.5, "region_type": "rainforest"},
    {
        "name": "Mississippi River Delta",
        "alt_names": ["Mississippi Delta"],
        "country": "United States",
        "lat": 29.6,
        "lon": -90.7,
        "region_type": "delta",
    },
    {"name": "Nile Delta", "country": "Egypt", "lat": 30.8, "lon": 31.0, "region_type": "delta"},
    {
        "name": "Alps",
        "alt_names": ["The Alps"],
        "lat": 46.5,
        "lon": 8.5,
        "region_type": "mountains",
    },
    {
        "name": "Altiplano",
        "alt_names": ["Andean Plateau"],
        "lat": -18.0,
        "lon": -67.5,
        "region_type": "plateau",
    },
    {"name": "Kalahari Desert", "lat": -22.5, "lon": 23.5, "region_type": "desert"},
    # The point is Longyearbyen, the place of the first example case.
    {
        "name": "Svalbard",
        "alt_names": ["Longyearbyen"],
        "country": "Norway",
        "lat": 78.22,
        "lon": 15.65,
        "region_type": "tundra",
    },
    # Open sea, where surface temperature is the sea-surface temperature. Both points answered
    # with real, varying sea values in live POWER calls on 14 November 2026.
    {"name": "Gulf of Maine", "lat": 43.0, "lon": -68.0, "region_type": "ocean"},
    {
        "name": "Equatorial Pacific",
        "alt_names": ["Pacific Ocean"],
        "lat": 0.0,
        "lon": -145.0,
        "region_type": "ocean",
    },
)


def read_country_names(country_info: Path) -> dict[str, str]:
    """Full country names keyed by ISO 3166 two-letter code."""
    names: dict[str, str] = {}
    for line in country_info.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        names[fields[COUNTRY_INFO_CODE_COLUMN]] = fields[COUNTRY_INFO_NAME_COLUMN]
    return names


def read_city_rows(cities_zip: Path) -> list[list[str]]:
    """The tab-separated rows of the city table, read from the archive without extracting it."""
    with zipfile.ZipFile(cities_zip) as archive, archive.open(CITIES_MEMBER) as table:
        lines = table.read().decode("utf-8").splitlines()
    rows = [line.split("\t") for line in lines if line]
    for row in rows:
        if len(row) != GEONAMES_COLUMNS:
            raise ValueError(f"Expected {GEONAMES_COLUMNS} columns, got {len(row)}: {row[:3]}")
    return rows


def city_record(row: list[str], country_names: dict[str, str]) -> dict[str, Any]:
    """One city in the places.json shape. Empty and absent fields are left out to keep it small."""
    name = row[NAME_COLUMN]
    ascii_name = row[ASCII_NAME_COLUMN]
    population = int(row[POPULATION_COLUMN])
    record: dict[str, Any] = {"name": name}
    if ascii_name and ascii_name != name:
        record["alt_names"] = [ascii_name]
    country = country_names.get(row[COUNTRY_CODE_COLUMN])
    if country:
        record["country"] = country
    record["lat"] = round(float(row[LATITUDE_COLUMN]), COORDINATE_DECIMALS)
    record["lon"] = round(float(row[LONGITUDE_COLUMN]), COORDINATE_DECIMALS)
    record["population"] = population
    record["kind"] = "city"
    if population >= MEGACITY_POPULATION:
        record["region_type"] = "megacity"
    return record


def region_record(region: dict[str, Any]) -> dict[str, Any]:
    """One hand-picked region in the places.json shape, with the same key order as a city."""
    record: dict[str, Any] = {"name": region["name"]}
    if region.get("alt_names"):
        record["alt_names"] = region["alt_names"]
    if region.get("country"):
        record["country"] = region["country"]
    record["lat"] = region["lat"]
    record["lon"] = region["lon"]
    record["kind"] = "region"
    record["region_type"] = region["region_type"]
    record["hand_picked"] = True
    return record


def attribution(downloaded: date) -> str:
    return (
        "Cities (kind 'city'): GeoNames (https://www.geonames.org/), file cities15000 from "
        f"https://download.geonames.org/export/dump/, downloaded {downloaded.isoformat()}, "
        "licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Changed: only places "
        f"of {MIN_CITY_POPULATION:,} people or more are kept, with fewer fields and coordinates "
        f"rounded to {COORDINATE_DECIMALS} decimals. Natural regions (kind 'region', marked "
        "hand_picked) were picked by hand with an AI coding assistant; each point is a "
        "representative spot inside the region, on land or at sea for an ocean, not a boundary."
    )


def build_places(cities_zip: Path, country_info: Path, downloaded: date) -> dict[str, Any]:
    """The places.json document: cities, most populous first, then the hand-picked regions."""
    country_names = read_country_names(country_info)
    rows = [
        row
        for row in read_city_rows(cities_zip)
        if int(row[POPULATION_COLUMN] or 0) >= MIN_CITY_POPULATION
        and row[FEATURE_CODE_COLUMN] not in EXCLUDED_FEATURE_CODES
    ]
    cities = [city_record(row, country_names) for row in rows]
    # A fixed order keeps the file stable between runs, so a rebuild gives a readable diff.
    cities.sort(key=lambda city: (-city["population"], city["name"], city["lat"], city["lon"]))
    regions = [region_record(region) for region in REGIONS]
    return {"attribution": attribution(downloaded), "places": cities + regions}


def to_json(document: dict[str, Any]) -> str:
    """JSON with one place per line, so the file stays compact and diffs stay readable."""
    place_lines = ",\n".join(
        "    " + json.dumps(place, ensure_ascii=False) for place in document["places"]
    )
    return (
        "{\n"
        f'  "attribution": {json.dumps(document["attribution"], ensure_ascii=False)},\n'
        '  "places": [\n'
        f"{place_lines}\n"
        "  ]\n"
        "}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cities_zip", type=Path, help="path to cities15000.zip from GeoNames")
    parser.add_argument("country_info", type=Path, help="path to countryInfo.txt from GeoNames")
    parser.add_argument(
        "--downloaded",
        type=date.fromisoformat,
        required=True,
        help="date the GeoNames files were downloaded, YYYY-MM-DD, for the attribution",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="where to write")
    args = parser.parse_args()
    document = build_places(args.cities_zip, args.country_info, args.downloaded)
    args.output.write_text(to_json(document), encoding="utf-8")
    print(f"Wrote {len(document['places'])} places to {args.output}")


if __name__ == "__main__":
    main()
