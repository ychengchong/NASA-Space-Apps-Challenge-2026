/**
 * The globe's map style (spec 11): the Earth as an engraving on OpenFreeMap tiles, in the ink
 * and paper of the page, with the layers the app fills in at run time, namely grid cells, a
 * region's box and place outlines. Nothing on it is coloured but data. OpenFreeMap needs no key;
 * its credit is shown on the stage and in the footer.
 */

import type { ExpressionSpecification, LayerSpecification, StyleSpecification } from "maplibre-gl";
import { graticuleFeatures } from "./globeGeometry";
import type { FeatureCollection } from "./globeGeometry";

const TILE_HOST = "https://tiles.openfreemap.org";

export const SOURCE = {
  cells: "cells",
  cellMarks: "cell-marks",
  box: "box",
  draftBox: "draft-box",
  placeCells: "place-cells",
  exampleLinks: "example-links",
} as const;

export const LAYER = {
  cellFill: "cell-fill",
  cellHatch: "cell-hatch",
  cellHover: "cell-hover",
} as const;

/** The fill of a cell without a result; the globe component supplies the image. */
export const HATCH_IMAGE = "no-result-hatch";

/** The fine lines engraved across the sea; the globe component supplies the image. */
export const SEA_IMAGE = "sea-lines";

/** The `index` no cell has, so the hover outline shows nothing. */
export const NO_CELL = -1;

// The sea is the darker paper, under its engraved lines and wherever their image is not ready.
const SEA = "#e0d5b8";
// Land is the paler paper, shaded by the relief image in grey.
const LAND = "#efe6cf";
const GRATICULE = "#6b5846";
const BORDER = "#7a5a3a";
const STATE_BORDER = "rgba(122, 90, 58, 0.55)";
const LABEL = "#2a2018";
const LABEL_HALO = "rgba(239, 230, 208, 0.95)";
const WATER_LABEL = "#5b4a3a";
const INK = "#2a2018";
const PAPER = "#f7f0de";
// The detective's red (styles.css, --accent), for the line between the places of one example.
const STRING = "#a3321c";
const HOVER_LINE_WIDTH = 2;
// The mark of a significant cell: a dark dot with a pale ring, readable on every fill and small
// enough to leave the cell's colour visible around it.
const MARK_RADIUS_PX = 2;
const MARK_RING_WIDTH = 1;

const EMPTY: FeatureCollection<never> = { type: "FeatureCollection", features: [] };

// Names in Latin script where the tiles have them, so every label can be read in English.
const NAME: ExpressionSpecification = [
  "coalesce",
  ["get", "name_en"],
  ["get", "name:latin"],
  ["get", "name"],
];
// The longest country names in the short forms small-scale maps print, so one name does not
// crowd its neighbours off the globe.
const COUNTRY_NAME: ExpressionSpecification = [
  "match",
  NAME,
  "Democratic Republic of the Congo",
  "DR Congo",
  "Republic of the Congo",
  "Congo",
  "Central African Republic",
  "Central African Rep.",
  NAME,
];
// The tiles class an ocean as a sea, so its name tells the two apart.
const IS_OCEAN: ExpressionSpecification = ["in", "Ocean", NAME];
const IS_POINT: ExpressionSpecification = ["==", ["geometry-type"], "Point"];
// The tiles rank the countries from 1, the best known, downward. The first rank covers the world
// thinly enough to be named on the whole Earth; the rest are named closer in.
const BEST_KNOWN_RANK = 1;
const SECOND_RANK = 2;
// From this zoom the view is of a region, with room for the seas and the other countries.
const REGION_VIEW_ZOOM = 3;
const HAS_RESULT: ExpressionSpecification = ["has", "colour"];

function labelPaint(colour: string): {
  "text-color": string;
  "text-halo-color": string;
  "text-halo-width": number;
} {
  return { "text-color": colour, "text-halo-color": LABEL_HALO, "text-halo-width": 1.4 };
}

function countryLabelLayer(id: string, ranks: ExpressionSpecification, minzoom = 0): LayerSpecification {
  return {
    id,
    type: "symbol",
    source: "openmaptiles",
    "source-layer": "place",
    minzoom,
    maxzoom: 8,
    filter: ["all", ["==", ["get", "class"], "country"], ranks],
    layout: {
      "text-field": COUNTRY_NAME,
      // Spaced capitals in a light weight, as countries are lettered on an engraved map.
      "text-font": ["Noto Sans Regular"],
      "text-size": ["interpolate", ["linear"], ["zoom"], 1, 9, 5, 13],
      "text-max-width": 6.25,
      "text-transform": "uppercase",
      "text-letter-spacing": 0.28,
      "text-padding": 6,
      "symbol-sort-key": ["get", "rank"],
    },
    paint: labelPaint(LABEL),
  };
}

function waterLabelLayer(
  id: string,
  waters: ExpressionSpecification,
  sizes: [number, number],
  minzoom = 0,
): LayerSpecification {
  return {
    id,
    type: "symbol",
    source: "openmaptiles",
    "source-layer": "water_name",
    minzoom,
    filter: ["all", IS_POINT, waters],
    layout: {
      "text-field": NAME,
      "text-font": ["Noto Sans Italic"],
      "text-size": ["interpolate", ["linear"], ["zoom"], 1, sizes[0], 6, sizes[1]],
      "text-letter-spacing": 0.15,
      "text-max-width": 6,
    },
    paint: labelPaint(WATER_LABEL),
  };
}

export const GLOBE_STYLE: StyleSpecification = {
  version: 8,
  projection: { type: "globe" },
  // An engraving has no glow of atmosphere round it.
  sky: { "atmosphere-blend": 0 },
  glyphs: `${TILE_HOST}/fonts/{fontstack}/{range}.pbf`,
  sources: {
    relief: {
      type: "raster",
      tiles: [`${TILE_HOST}/natural_earth/ne2sr/{z}/{x}/{y}.png`],
      tileSize: 256,
      maxzoom: 6,
    },
    openmaptiles: { type: "vector", url: `${TILE_HOST}/planet` },
    graticule: { type: "geojson", data: graticuleFeatures() },
    [SOURCE.cells]: { type: "geojson", data: EMPTY },
    [SOURCE.cellMarks]: { type: "geojson", data: EMPTY },
    [SOURCE.box]: { type: "geojson", data: EMPTY },
    [SOURCE.draftBox]: { type: "geojson", data: EMPTY },
    [SOURCE.placeCells]: { type: "geojson", data: EMPTY },
    [SOURCE.exampleLinks]: { type: "geojson", data: EMPTY },
  },
  layers: [
    { id: "land", type: "background", paint: { "background-color": LAND } },
    {
      id: "relief",
      type: "raster",
      source: "relief",
      // The relief image without its colours, faint: the shading of an engraving.
      paint: {
        "raster-opacity": 0.38,
        "raster-saturation": -1,
        "raster-brightness-min": 0.25,
        "raster-contrast": 0.35,
      },
    },
    {
      id: "water",
      type: "fill",
      source: "openmaptiles",
      "source-layer": "water",
      filter: ["!=", ["get", "brunnel"], "tunnel"],
      paint: { "fill-color": SEA },
    },
    {
      id: "water-lines",
      type: "fill",
      source: "openmaptiles",
      "source-layer": "water",
      filter: ["!=", ["get", "brunnel"], "tunnel"],
      paint: { "fill-pattern": SEA_IMAGE },
    },
    {
      id: "river",
      type: "line",
      source: "openmaptiles",
      "source-layer": "waterway",
      minzoom: 4,
      filter: ["==", ["get", "class"], "river"],
      paint: { "line-color": GRATICULE, "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.4, 8, 1.4] },
    },
    {
      id: "graticule",
      type: "line",
      source: "graticule",
      paint: { "line-color": GRATICULE, "line-opacity": 0.4, "line-width": 0.6 },
    },
    {
      id: LAYER.cellFill,
      type: "fill",
      source: SOURCE.cells,
      filter: HAS_RESULT,
      // Cells meet without edges, so the colours read as one field. They are opaque, so a rate
      // has the colour of the key wherever it lies, over land or sea.
      paint: { "fill-color": ["get", "colour"], "fill-antialias": false },
    },
    {
      id: LAYER.cellHatch,
      type: "fill",
      source: SOURCE.cells,
      filter: ["!", HAS_RESULT],
      paint: { "fill-pattern": HATCH_IMAGE },
    },
    // The coast, drawn over the cells from the region view on, because opaque cells hide the
    // meeting of land and sea under them.
    {
      id: "coast",
      type: "line",
      source: "openmaptiles",
      "source-layer": "water",
      minzoom: REGION_VIEW_ZOOM,
      filter: ["!=", ["get", "brunnel"], "tunnel"],
      paint: { "line-color": INK, "line-opacity": 0.55, "line-width": 0.8 },
    },
    {
      id: "state-border",
      type: "line",
      source: "openmaptiles",
      "source-layer": "boundary",
      minzoom: 4,
      filter: ["all", ["==", ["get", "admin_level"], 4], ["!=", ["get", "maritime"], 1]],
      paint: { "line-color": STATE_BORDER, "line-width": 0.6, "line-dasharray": [2, 2] },
    },
    {
      id: "country-border",
      type: "line",
      source: "openmaptiles",
      "source-layer": "boundary",
      filter: ["all", ["==", ["get", "admin_level"], 2], ["!=", ["get", "maritime"], 1]],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": BORDER,
        "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.6, 5, 1, 8, 1.6],
      },
    },
    {
      id: LAYER.cellHover,
      type: "line",
      source: SOURCE.cells,
      filter: ["==", ["get", "index"], NO_CELL],
      paint: { "line-color": INK, "line-width": HOVER_LINE_WIDTH },
    },
    {
      id: "cell-mark",
      type: "circle",
      source: SOURCE.cellMarks,
      paint: {
        "circle-radius": MARK_RADIUS_PX,
        "circle-color": INK,
        "circle-stroke-color": PAPER,
        "circle-stroke-width": MARK_RING_WIDTH,
      },
    },
    {
      id: "place-cell-fill",
      type: "fill",
      source: SOURCE.placeCells,
      paint: { "fill-color": ["get", "colour"], "fill-opacity": 0.22 },
    },
    {
      id: "place-cell-line",
      type: "line",
      source: SOURCE.placeCells,
      paint: { "line-color": ["get", "colour"], "line-width": 2 },
    },
    {
      id: "example-link",
      type: "line",
      source: SOURCE.exampleLinks,
      layout: { "line-cap": "round" },
      paint: { "line-color": STRING, "line-width": 1.5 },
    },
    // A region's box: a dashed line of ink on a pale one, so it shows on land, sea and cells.
    {
      id: "box-casing",
      type: "line",
      source: SOURCE.box,
      paint: { "line-color": PAPER, "line-width": 4, "line-opacity": 0.9 },
    },
    {
      id: "box-line",
      type: "line",
      source: SOURCE.box,
      paint: { "line-color": INK, "line-width": 2, "line-dasharray": [3, 2] },
    },
    {
      id: "draft-box-fill",
      type: "fill",
      source: SOURCE.draftBox,
      paint: { "fill-color": INK, "fill-opacity": 0.12 },
    },
    {
      id: "draft-box-line",
      type: "line",
      source: SOURCE.draftBox,
      paint: { "line-color": INK, "line-width": 2 },
    },
    // Waters are named from the region view on. On the whole Earth an ocean's name lies near the
    // edge of the disc, where it would run under the ring of degree marks.
    waterLabelLayer("sea-label", ["!", IS_OCEAN], [10, 12], REGION_VIEW_ZOOM),
    waterLabelLayer("ocean-label", IS_OCEAN, [11, 14], REGION_VIEW_ZOOM),
    {
      id: "town-label",
      type: "symbol",
      source: "openmaptiles",
      "source-layer": "place",
      minzoom: 6,
      filter: ["==", ["get", "class"], "town"],
      layout: {
        "text-field": NAME,
        "text-font": ["Noto Sans Regular"],
        "text-size": 11,
        "text-max-width": 8,
      },
      paint: labelPaint(LABEL),
    },
    {
      id: "city-label",
      type: "symbol",
      source: "openmaptiles",
      "source-layer": "place",
      minzoom: 3,
      filter: ["==", ["get", "class"], "city"],
      layout: {
        "text-field": NAME,
        "text-font": ["Noto Sans Regular"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 3, 10, 7, 13],
        "text-max-width": 8,
        "symbol-sort-key": ["get", "rank"],
      },
      paint: labelPaint(LABEL),
    },
    // The best known countries are named from the whole-Earth view on, wherever their names have
    // room; the others join closer in. A later layer places its names first, so where two names
    // would overlap, the better known country keeps its name.
    countryLabelLayer("small-country-label", [">", ["get", "rank"], SECOND_RANK], REGION_VIEW_ZOOM),
    countryLabelLayer("country-label", ["==", ["get", "rank"], SECOND_RANK], REGION_VIEW_ZOOM),
    countryLabelLayer("large-country-label", ["==", ["get", "rank"], BEST_KNOWN_RANK]),
  ],
};
