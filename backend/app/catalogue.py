"""The curated variable catalogue (spec 6, "Starter catalogue" and "A catalogue entry")."""

import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.config import DATA_DIR
from app.errors import UnknownVariableError
from app.models import VariableSummary

CATALOGUE_PATH = DATA_DIR / "catalogue.json"


class GridAlignment(StrEnum):
    """Where a grid's cells lie relative to the multiples of the cell size (spec 6, "Places and
    grid cells").
    """

    # The MERRA-2 grid: each cell is centred on a grid point, a multiple of the cell size, with
    # its edges halfway between grid points. A place takes the nearest grid point.
    CENTRED_ON_MULTIPLES = "centred_on_multiples"
    # The 1° grid of sunlight and cloud: each cell's edges are multiples of the cell size, such
    # as whole degrees, so its centre lies halfway between them. A place takes the cell that
    # holds it, and a place on an edge the cell north or east of it.
    BOUNDED_BY_MULTIPLES = "bounded_by_multiples"


class GridSize(BaseModel):
    """A variable's grid: its cell size in degrees and how its cells are aligned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    height: float
    width: float
    alignment: GridAlignment


class CatalogueEntry(BaseModel):
    """One catalogue entry, including the fields that never leave the server, such as `code`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    code: str
    name: str
    definition: str
    keywords: tuple[str, ...]
    units: str
    rate_units: str
    decimals: int
    record_start: int
    grid: GridSize
    theme: str
    related: tuple[str, ...]
    # Region types of places.json where a trend in this variable is worth testing (spec 6).
    region_types: tuple[str, ...] = ()
    trend_note: str | None = None
    source_changes: tuple[int, ...] = ()
    # Spec 7, "The whole world": whether the frozen world-mean sample covers this variable. Land-
    # only and sea-only quantities are left out, since a world mean of them means nothing.
    world_mean: bool = False
    source: str


@lru_cache(maxsize=4)
def load_catalogue(path: Path = CATALOGUE_PATH) -> tuple[CatalogueEntry, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(CatalogueEntry.model_validate(item) for item in raw)


def get_entry(variable_id: str) -> CatalogueEntry:
    """Return the entry for a catalogue id, or raise `UnknownVariableError`."""
    for entry in load_catalogue():
        if entry.id == variable_id:
            return entry
    raise UnknownVariableError(f"'{variable_id}' is not a variable in the catalogue.")


def to_summary(entry: CatalogueEntry) -> VariableSummary:
    return VariableSummary(
        id=entry.id,
        name=entry.name,
        definition=entry.definition,
        units=entry.units,
        rate_units=entry.rate_units,
        decimals=entry.decimals,
        theme=entry.theme,
        record_start=entry.record_start,
        related=list(entry.related),
        region_types=list(entry.region_types),
        trend_note=entry.trend_note,
        source_changes=list(entry.source_changes) or None,
        world_mean=entry.world_mean,
    )
