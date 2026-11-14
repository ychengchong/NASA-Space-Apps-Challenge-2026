/**
 * The geometry of the region view (spec 7, "Region view", and spec 10, `/api/map`): the box a
 * map covers and the grid cells drawn inside it. Nothing here computes a statistic.
 */

import type { Box, MapCell } from "./api";
import type { Corner } from "./mapCell";
import { MERRA2_CELL_HEIGHT, MERRA2_CELL_WIDTH } from "./mapCell";

// Spec 10: each side of a map's box is at most 10°.
export const MAX_BOX_SIDE_DEGREES = 10;
// Spec 5: latitude runs from -90 to 90 and longitude from -180 to 180.
const MAX_LATITUDE = 90;
const MAX_LONGITUDE = 180;
// Grid steps are rounded to this many decimals, which drops float noise from the differences.
const STEP_DECIMALS = 6;

export interface LatLon {
  lat: number;
  lon: number;
}

export interface GridSteps {
  /** Degrees of latitude between neighbouring grid points. */
  height: number;
  /** Degrees of longitude between neighbouring grid points. */
  width: number;
}

/**
 * The box of a "Map this region" link: 10° by 10° around the place, moved inward where it would
 * reach past a pole or the 180° meridian, so it stays inside the globe and keeps its size.
 *
 * Its edges sit on whole degrees. NASA POWER compares the plain float difference of the edges
 * with its 10° limit, so 63.98 to 73.98 (a difference of 10.000000000000007) is refused, while
 * whole-degree edges give exactly 10.
 */
export function boxAroundPlace(place: LatLon): Box {
  const half = MAX_BOX_SIDE_DEGREES / 2;
  const south = clamp(Math.round(place.lat) - half, -MAX_LATITUDE, MAX_LATITUDE - MAX_BOX_SIDE_DEGREES);
  const west = clamp(Math.round(place.lon) - half, -MAX_LONGITUDE, MAX_LONGITUDE - MAX_BOX_SIDE_DEGREES);
  return { south, west, north: south + MAX_BOX_SIDE_DEGREES, east: west + MAX_BOX_SIDE_DEGREES };
}

/**
 * The box drawn by dragging from `start` to `end`: widened to whole degrees, kept inside the
 * globe, and cut to at most 10° a side, measured from the corner where the drag started.
 * Whether the box is large enough is left to the API, which explains its own limits.
 */
export function boxFromDrag(start: LatLon, end: LatLon): Box {
  const [south, north] = sideFromDrag(start.lat, end.lat, MAX_LATITUDE);
  const [west, east] = sideFromDrag(start.lon, end.lon, MAX_LONGITUDE);
  return { south, west, north, east };
}

function sideFromDrag(start: number, end: number, limit: number): [number, number] {
  const low = clamp(Math.floor(Math.min(start, end)), -limit, limit);
  const high = clamp(Math.ceil(Math.max(start, end)), -limit, limit);
  if (high - low <= MAX_BOX_SIDE_DEGREES) return [low, high];
  // Keep the edge nearest the drag's starting point, and cut the far side.
  return start <= end ? [low, low + MAX_BOX_SIDE_DEGREES] : [high - MAX_BOX_SIDE_DEGREES, high];
}

/**
 * The spacing of the grid the cells sit on: the smallest gap between neighbouring grid points
 * in each direction. Spec 6: meteorological variables come on the 0.5° by 0.625° MERRA-2 grid,
 * while sunlight and cloud come back from a regional call in 1° cells. A direction with a
 * single row or column of cells falls back to the MERRA-2 step.
 */
export function gridSteps(cells: readonly LatLon[]): GridSteps {
  return {
    height: smallestGap(cells.map((cell) => cell.lat)) ?? MERRA2_CELL_HEIGHT,
    width: smallestGap(cells.map((cell) => cell.lon)) ?? MERRA2_CELL_WIDTH,
  };
}

function smallestGap(values: readonly number[]): number | null {
  const sorted = [...new Set(values)].sort((a, b) => a - b);
  let smallest: number | null = null;
  for (let index = 1; index < sorted.length; index += 1) {
    const gap = (sorted[index] ?? 0) - (sorted[index - 1] ?? 0);
    if (smallest === null || gap < smallest) smallest = gap;
  }
  return smallest === null ? null : Number(smallest.toFixed(STEP_DECIMALS));
}

/** A cell's rectangle as its south-west and north-east corners, centred on its grid point. */
export function cellBounds(cell: Pick<MapCell, "lat" | "lon">, steps: GridSteps): [Corner, Corner] {
  const halfHeight = steps.height / 2;
  const halfWidth = steps.width / 2;
  return [
    [cell.lat - halfHeight, cell.lon - halfWidth],
    [cell.lat + halfHeight, cell.lon + halfWidth],
  ];
}

/** The box as its south-west and north-east corners. */
export function boxCorners(box: Box): [Corner, Corner] {
  return [
    [box.south, box.west],
    [box.north, box.east],
  ];
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}
