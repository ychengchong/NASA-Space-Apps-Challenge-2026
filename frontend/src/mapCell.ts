/**
 * The outline of a place's grid cell on the place map, and the part of the map that holds the places
 * and their cells (spec 6, "Places and grid cells").
 */

import type { Cell } from "./api";

// Spec 6: the MERRA-2 grid has a point every 0.5° of latitude and 0.625° of longitude.
export const MERRA2_CELL_HEIGHT = 0.5;
export const MERRA2_CELL_WIDTH = 0.625;

/** A corner as [latitude, longitude] in degrees. */
export type Corner = [number, number];

/**
 * The cell's outline as its south-west and north-east corners. The API gives every cell by its
 * centre and size: a MERRA-2 cell around its grid point, and a 1° cell of sunlight and cloud
 * between whole degrees.
 */
export function cellOutline(cell: Cell): [Corner, Corner] {
  const halfHeight = cell.height / 2;
  const halfWidth = cell.width / 2;
  return [
    [cell.lat - halfHeight, cell.lon - halfWidth],
    [cell.lat + halfHeight, cell.lon + halfWidth],
  ];
}

const FULL_TURN_DEG = 360;

/** A place on the place map: its point and, once a case has run, the grid cell the API analysed. */
export interface PlaceOnMap {
  lat: number;
  lon: number;
  cell?: Cell;
}

/**
 * The outline of the place's cell, on the same side of the antimeridian as the place, or
 * undefined when the place has no cell. The API wraps a cell's centre into -180° to 180°, so a
 * place at 179.8°E can have its cell centred on 180°W; the outline then moves by a whole turn of
 * longitude to sit next to the place's marker.
 */
export function placeCellOutline(place: PlaceOnMap): [Corner, Corner] | undefined {
  const { cell } = place;
  if (cell === undefined) return undefined;
  const turns = Math.round((place.lon - cell.lon) / FULL_TURN_DEG);
  return cellOutline({ ...cell, lon: cell.lon + turns * FULL_TURN_DEG });
}

/**
 * The south-west and north-east corners of the smallest box that holds every place's point and
 * the outline of its cell, or undefined when there are no places. A 1° cell can reach a whole
 * degree beyond its place, so the map fits the cells as well as the points.
 */
export function placesExtent(places: readonly PlaceOnMap[]): [Corner, Corner] | undefined {
  const corners = places.flatMap((place): Corner[] => [
    [place.lat, place.lon],
    ...(placeCellOutline(place) ?? []),
  ]);
  if (corners.length === 0) return undefined;
  const lats = corners.map(([lat]) => lat);
  const lons = corners.map(([, lon]) => lon);
  return [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ];
}
