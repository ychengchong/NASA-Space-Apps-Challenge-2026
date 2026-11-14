/**
 * What the globe draws, as GeoJSON, and where its camera sits (spec 3, "The globe"). Nothing here
 * needs a browser or computes a statistic.
 */

import type { Box, MapCell } from "./api";
import { slopeColour } from "./colourScale";
import type { ExamplePin } from "./examplePins";
import type { Corner, PlaceOnMap } from "./mapCell";
import { placeCellOutline, placesExtent } from "./mapCell";
import { placeStyle } from "./placeStyles";
import { boxCorners, cellBounds, gridSteps } from "./regionBox";
import type { LatLon } from "./regionBox";

/** A position as [longitude, latitude] in degrees, the order GeoJSON uses. */
export type Position = [number, number];

export type PolygonFeature<Properties> = {
  type: "Feature";
  properties: Properties;
  geometry: { type: "Polygon"; coordinates: Position[][] };
};

export type PointFeature<Properties> = {
  type: "Feature";
  properties: Properties;
  geometry: { type: "Point"; coordinates: Position };
};

export type LineFeature<Properties> = {
  type: "Feature";
  properties: Properties;
  geometry: { type: "LineString"; coordinates: Position[] };
};

export type FeatureCollection<Feature> = { type: "FeatureCollection"; features: Feature[] };

/** The outline colour of a place's cell. */
export type PlaceCellProperties = { colour: string };

/**
 * A region cell: its position in the map's `cells`, and its fill colour. A cell without a result
 * has no `colour`, and the globe draws it hatched.
 */
export type RegionCellProperties = { index: number; colour?: string };

export type NoProperties = Record<string, never>;

export interface Size {
  width: number;
  height: number;
}

/** Distances in pixels from each edge of the viewport. */
export interface Edges {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

/** A rectangle in the viewport, in pixels from its top left corner. */
export interface Rect extends Size {
  top: number;
  left: number;
}

// The share of the stage's shorter side that the whole Earth fills.
const EARTH_FILL = 0.8;
// The width of the whole world at zoom 0 in MapLibre, in pixels.
const WORLD_SIZE_PX = 512;
// Toward a pole the cosine of the latitude goes to zero, and the zoom with it; the Earth is sized
// as if no place were nearer a pole than this.
const MAX_SIZING_LATITUDE = 85;
// The furthest the whole-Earth view leans toward a pole. Facing a place nearer a pole than this
// would show the Earth from above it, with the continents lying on their sides.
const MAX_FACING_LATITUDE = 55;
const DEGREES_TO_RADIANS = Math.PI / 180;
// The graticule: a meridian and a parallel every this many degrees.
const GRATICULE_STEP = 15;
// Each of its lines has a point every this many degrees, so it bends with the globe.
const GRATICULE_POINT_STEP = 2;
// The map's tiles end near 85° of latitude, so the meridians stop just short of it, and the last
// parallels are the ones 15° from each pole.
const GRATICULE_MERIDIAN_END = 84;
const GRATICULE_LAST_PARALLEL = 75;
const HALF_TURN = 180;
/**
 * The ring of degree marks reaches this many times the radius of the Earth's disc from its
 * centre (StageRing draws it; styles.css sizes it to twice this).
 */
export const RING_REACH = 1.1;

/** The features as one GeoJSON collection. */
export function collection<Feature>(features: Feature[]): FeatureCollection<Feature> {
  return { type: "FeatureCollection", features };
}

/** A rectangle between a south-west and a north-east corner, as a closed GeoJSON ring. */
export function rectangle<Properties>(
  [[south, west], [north, east]]: [Corner, Corner],
  properties: Properties,
): PolygonFeature<Properties> {
  const ring: Position[] = [
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
  ];
  return { type: "Feature", properties, geometry: { type: "Polygon", coordinates: [ring] } };
}

/**
 * The outline of each place's grid cell, in the place's own colour. A place without a cell, as
 * before its case has run, gives no outline.
 */
export function placeCellFeatures(
  places: readonly PlaceOnMap[],
): FeatureCollection<PolygonFeature<PlaceCellProperties>> {
  const features: PolygonFeature<PlaceCellProperties>[] = [];
  places.forEach((place, index) => {
    const outline = placeCellOutline(place);
    if (outline !== undefined) features.push(rectangle(outline, { colour: placeStyle(index).color }));
  });
  return collection(features);
}

/**
 * Every cell of a region map as a rectangle around its grid point, cut at the edge of `box`, so
 * the map ends where the box does: a cell whose grid point lies on an edge reaches half a cell
 * past it. A cell with a result carries the colour of its rate on a scale that runs from -limit
 * to +limit. A cell that lies wholly outside the box is left out.
 */
export function regionCellFeatures(
  cells: readonly MapCell[],
  limit: number,
  box: Box,
): FeatureCollection<PolygonFeature<RegionCellProperties>> {
  const steps = gridSteps(cells);
  const features: PolygonFeature<RegionCellProperties>[] = [];
  cells.forEach((cell, index) => {
    const corners = insideBox(cellBounds(cell, steps), box);
    if (corners === undefined) return;
    const properties =
      cell.sen_slope === null ? { index } : { index, colour: slopeColour(cell.sen_slope, limit) };
    features.push(rectangle(corners, properties));
  });
  return collection(features);
}

/** The part of a rectangle that lies inside the box, or undefined when none of it does. */
function insideBox([[south, west], [north, east]]: [Corner, Corner], box: Box): [Corner, Corner] | undefined {
  const cut: [Corner, Corner] = [
    [Math.max(south, box.south), Math.max(west, box.west)],
    [Math.min(north, box.north), Math.min(east, box.east)],
  ];
  const [[cutSouth, cutWest], [cutNorth, cutEast]] = cut;
  return cutSouth < cutNorth && cutWest < cutEast ? cut : undefined;
}

/** The grid point of each cell that passes the map's stricter test, where its mark is drawn. */
export function regionMarkFeatures(cells: readonly MapCell[]): FeatureCollection<PointFeature<NoProperties>> {
  return collection(
    cells
      .filter((cell) => cell.significant)
      .map((cell) => ({
        type: "Feature" as const,
        properties: {},
        geometry: { type: "Point" as const, coordinates: [cell.lon, cell.lat] as Position },
      })),
  );
}

/** The box of a region map as a rectangle. */
export function boxFeature(box: Box): PolygonFeature<NoProperties> {
  return rectangle(boxCorners(box), {});
}

/** The centre of a box. */
export function boxCentre(box: Box): LatLon {
  return { lat: (box.south + box.north) / 2, lon: (box.west + box.east) / 2 };
}

/**
 * The point the globe turns toward to show the places: the centre of the smallest box that holds
 * them and their cells, or undefined when there are no places.
 */
export function placesCentre(places: readonly PlaceOnMap[]): LatLon | undefined {
  const extent = placesExtent(places);
  if (extent === undefined) return undefined;
  const [[south, west], [north, east]] = extent;
  return { lat: (south + north) / 2, lon: (west + east) / 2 };
}

/**
 * The point the whole-Earth view faces to show `centre`: the same longitude, and the latitude
 * held within MAX_FACING_LATITUDE of the equator. A place nearer a pole is then seen above or
 * below the middle of the Earth, which stays the right way up.
 */
export function earthFacing(centre: LatLon): LatLon {
  const lat = Math.max(-MAX_FACING_LATITUDE, Math.min(MAX_FACING_LATITUDE, centre.lat));
  return { lat, lon: centre.lon };
}

/**
 * The zoom at which the whole Earth fits the stage with the globe centred on latitude `lat`.
 * MapLibre keeps a zoom level's scale true at the centre of the view, so at one zoom the globe is
 * drawn larger the nearer its centre is to a pole; the cosine takes that back out.
 */
export function earthZoom(stage: Size, lat: number): number {
  const radius = (EARTH_FILL * Math.min(stage.width, stage.height)) / 2;
  const sizingLat = Math.min(Math.abs(lat), MAX_SIZING_LATITUDE);
  const circumference = 2 * Math.PI * radius * Math.cos(sizingLat * DEGREES_TO_RADIANS);
  return Math.log2(circumference / WORLD_SIZE_PX);
}

/**
 * The part of the viewport outside the stage, as the padding that keeps the globe's centre in
 * the middle of the stage. A stage that reaches past the viewport gives no negative padding.
 */
export function stagePadding(stage: Rect, viewport: Size): Edges {
  const inside = (distance: number): number => Math.max(0, Math.round(distance));
  return {
    top: inside(stage.top),
    left: inside(stage.left),
    right: inside(viewport.width - (stage.left + stage.width)),
    bottom: inside(viewport.height - (stage.top + stage.height)),
  };
}

/**
 * The radius in pixels of the Earth's disc as the globe draws it at `zoom`, facing latitude
 * `lat`. The globe is a sphere seen by a camera `fieldOfView` degrees tall over a viewport
 * `viewportHeight` pixels high, so the disc is a little smaller than the sphere. A latitude
 * nearer a pole than 85° is sized as 85°, as in `earthZoom`.
 */
export function earthDiscRadius(
  zoom: number,
  lat: number,
  viewportHeight: number,
  fieldOfView: number,
): number {
  const sphere = sphereRadius(zoom, lat);
  const camera = cameraDistance(viewportHeight, fieldOfView);
  return (camera * sphere) / Math.sqrt(camera * (camera + 2 * sphere));
}

/**
 * True when `point` is on the side of the Earth the globe shows while it faces `centre` at
 * `zoom`: nearer to `centre`, round the Earth, than the horizon the camera sees. The camera is
 * `fieldOfView` degrees tall over a viewport `viewportHeight` pixels high.
 */
export function isInView(
  centre: LatLon,
  point: LatLon,
  zoom: number,
  viewportHeight: number,
  fieldOfView: number,
): boolean {
  const sphere = sphereRadius(zoom, centre.lat);
  // The cosine of the angle, at the Earth's centre, from the point the globe faces to its horizon.
  const horizon = sphere / (cameraDistance(viewportHeight, fieldOfView) + sphere);
  const [fromLat, toLat] = [centre.lat * DEGREES_TO_RADIANS, point.lat * DEGREES_TO_RADIANS];
  const turn = (point.lon - centre.lon) * DEGREES_TO_RADIANS;
  const toPoint = Math.sin(fromLat) * Math.sin(toLat) + Math.cos(fromLat) * Math.cos(toLat) * Math.cos(turn);
  return toPoint > horizon;
}

/** The radius in pixels of the sphere the globe draws at `zoom`, facing latitude `lat`. */
function sphereRadius(zoom: number, lat: number): number {
  const sizingLat = Math.min(Math.abs(lat), MAX_SIZING_LATITUDE);
  return (WORLD_SIZE_PX * 2 ** zoom) / (2 * Math.PI * Math.cos(sizingLat * DEGREES_TO_RADIANS));
}

/** How far in pixels the globe's camera stands from the point of the Earth it faces. */
function cameraDistance(viewportHeight: number, fieldOfView: number): number {
  return viewportHeight / 2 / Math.tan((fieldOfView / 2) * DEGREES_TO_RADIANS);
}

/**
 * The line that joins the places of an example case which tests more than one place, from the
 * first place to the last. A case with one place has no line.
 */
export function exampleLinkFeatures(
  pins: readonly ExamplePin[],
): FeatureCollection<LineFeature<NoProperties>> {
  return collection(
    pins
      .filter((pin) => pin.places.length > 1)
      .map((pin) => ({
        type: "Feature" as const,
        properties: {},
        geometry: {
          type: "LineString" as const,
          coordinates: pin.places.map((place): Position => [place.lon, place.lat]),
        },
      })),
  );
}

/** True when the Earth's disc of `radius` pixels, with its ring of degree marks, fits the stage. */
export function ringFits(radius: number, stage: Size): boolean {
  return 2 * radius * RING_REACH <= Math.min(stage.width, stage.height);
}

/**
 * The lines of longitude and latitude engraved on the globe: one every 15°, each as a line of
 * points 2° apart. The meridians run from 84°S to 84°N, and the parallels from 75°S to 75°N.
 */
export function graticuleFeatures(): FeatureCollection<LineFeature<NoProperties>> {
  const line = (coordinates: Position[]): LineFeature<NoProperties> => ({
    type: "Feature",
    properties: {},
    geometry: { type: "LineString", coordinates },
  });
  const features: LineFeature<NoProperties>[] = [];
  for (let lon = -HALF_TURN; lon < HALF_TURN; lon += GRATICULE_STEP) {
    const meridian: Position[] = [];
    for (let lat = -GRATICULE_MERIDIAN_END; lat <= GRATICULE_MERIDIAN_END; lat += GRATICULE_POINT_STEP) {
      meridian.push([lon, lat]);
    }
    features.push(line(meridian));
  }
  for (let lat = -GRATICULE_LAST_PARALLEL; lat <= GRATICULE_LAST_PARALLEL; lat += GRATICULE_STEP) {
    const parallel: Position[] = [];
    for (let lon = -HALF_TURN; lon <= HALF_TURN; lon += GRATICULE_POINT_STEP) parallel.push([lon, lat]);
    features.push(line(parallel));
  }
  return collection(features);
}
