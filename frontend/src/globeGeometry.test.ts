import { describe, expect, test } from "vitest";
import type { Box, MapCell } from "./api";
import { slopeColour } from "./colourScale";
import {
  boxCentre,
  boxFeature,
  earthDiscRadius,
  earthFacing,
  earthZoom,
  exampleLinkFeatures,
  graticuleFeatures,
  isInView,
  placeCellFeatures,
  placesCentre,
  rectangle,
  regionCellFeatures,
  regionMarkFeatures,
  ringFits,
  stagePadding,
} from "./globeGeometry";
import { placeStyle } from "./placeStyles";

const MERRA2_CELL = { lat: 60, lon: 25, height: 0.5, width: 0.625 };

function cell(lat: number, lon: number, slope: number | null, significant = false): MapCell {
  return { lat, lon, sen_slope: slope, mk_p: slope === null ? null : 0.01, significant };
}

describe("rectangle", () => {
  test("is a closed ring of longitude and latitude pairs, from the south-west corner", () => {
    const feature = rectangle(
      [
        [55, 20],
        [65, 30],
      ],
      {},
    );
    expect(feature.geometry.coordinates).toEqual([
      [
        [20, 55],
        [30, 55],
        [30, 65],
        [20, 65],
        [20, 55],
      ],
    ]);
  });
});

describe("placeCellFeatures", () => {
  test("outlines each place's cell in the place's own colour", () => {
    const { features } = placeCellFeatures([
      { lat: 60.17, lon: 24.94, cell: MERRA2_CELL },
      { lat: 37.98, lon: 23.73, cell: { lat: 38, lon: 23.75, height: 0.5, width: 0.625 } },
    ]);
    expect(features.map((feature) => feature.properties.colour)).toEqual([
      placeStyle(0).color,
      placeStyle(1).color,
    ]);
    expect(features[0]?.geometry.coordinates[0]?.[0]).toEqual([24.6875, 59.75]);
  });

  test("keeps a place's colour when an earlier place has no cell yet", () => {
    const { features } = placeCellFeatures([
      { lat: 37.98, lon: 23.73 },
      { lat: 60.17, lon: 24.94, cell: MERRA2_CELL },
    ]);
    expect(features).toHaveLength(1);
    expect(features[0]?.properties.colour).toBe(placeStyle(1).color);
  });

  test("draws a cell across the 180° meridian on the side of its place", () => {
    const { features } = placeCellFeatures([
      { lat: 0.1, lon: 179.8, cell: { lat: 0, lon: -180, height: 0.5, width: 0.625 } },
    ]);
    expect(features[0]?.geometry.coordinates[0]?.[0]).toEqual([179.6875, -0.25]);
  });
});

describe("regionCellFeatures", () => {
  const cells = [cell(60, 25, 0.5), cell(60, 25.625, null), cell(60.5, 25, -0.25)];
  const BOX: Box = { south: 55, west: 20, north: 65, east: 30 };

  test("gives each cell with a result the colour of its rate on the scale", () => {
    const { features } = regionCellFeatures(cells, 0.5, BOX);
    expect(features[0]?.properties.colour).toBe(slopeColour(0.5, 0.5));
    expect(features[2]?.properties.colour).toBe(slopeColour(-0.25, 0.5));
  });

  test("gives a cell without a result no colour, so the globe hatches it", () => {
    const { features } = regionCellFeatures(cells, 0.5, BOX);
    expect(features[1]?.properties).toEqual({ index: 1 });
  });

  test("numbers the cells by their place in the map's list", () => {
    const { features } = regionCellFeatures(cells, 0.5, BOX);
    expect(features.map((feature) => feature.properties.index)).toEqual([0, 1, 2]);
  });

  test("draws each cell as a rectangle around its grid point, one grid step wide and tall", () => {
    const { features } = regionCellFeatures(cells, 0.5, BOX);
    expect(features[0]?.geometry.coordinates[0]).toEqual([
      [24.6875, 59.75],
      [25.3125, 59.75],
      [25.3125, 60.25],
      [24.6875, 60.25],
      [24.6875, 59.75],
    ]);
  });

  test("cuts a cell at the edge of the box, so the map ends where the box does", () => {
    const edgeBox: Box = { south: 60, west: 25, north: 65, east: 30 };
    const { features } = regionCellFeatures(cells, 0.5, edgeBox);
    expect(features[0]?.geometry.coordinates[0]).toEqual([
      [25, 60],
      [25.3125, 60],
      [25.3125, 60.25],
      [25, 60.25],
      [25, 60],
    ]);
  });

  test("leaves out a cell that lies wholly outside the box, and keeps the others' numbers", () => {
    const northBox: Box = { south: 60.3, west: 20, north: 65, east: 30 };
    const { features } = regionCellFeatures(cells, 0.5, northBox);
    expect(features.map((feature) => feature.properties.index)).toEqual([2]);
  });
});

describe("regionMarkFeatures", () => {
  test("marks only the cells that pass the map's stricter test, at their grid points", () => {
    const { features } = regionMarkFeatures([cell(60, 25, 0.5, true), cell(60, 25.625, 0.1)]);
    expect(features.map((feature) => feature.geometry.coordinates)).toEqual([[25, 60]]);
  });
});

describe("boxFeature and boxCentre", () => {
  const box = { south: 55, west: 20, north: 65, east: 30 };

  test("draws the box from its south-west to its north-east corner", () => {
    const [ring] = boxFeature(box).geometry.coordinates;
    expect(ring?.[0]).toEqual([20, 55]);
    expect(ring?.[2]).toEqual([30, 65]);
  });

  test("finds the middle of the box", () => {
    expect(boxCentre(box)).toEqual({ lat: 60, lon: 25 });
  });
});

describe("placesCentre", () => {
  test("is undefined when there is no place to face", () => {
    expect(placesCentre([])).toBeUndefined();
  });

  test("is the place itself for one place without a cell", () => {
    expect(placesCentre([{ lat: -1.29, lon: 36.82 }])).toEqual({ lat: -1.29, lon: 36.82 });
  });

  test("is the middle of the box that holds every place", () => {
    expect(
      placesCentre([
        { lat: 60, lon: 20 },
        { lat: 40, lon: 30 },
      ]),
    ).toEqual({ lat: 50, lon: 25 });
  });
});

describe("earthFacing", () => {
  test("faces a place in the middle latitudes straight on", () => {
    expect(earthFacing({ lat: 48.2, lon: 16.4 })).toEqual({ lat: 48.2, lon: 16.4 });
  });

  test("leans no further than 55 degrees toward the north pole, keeping the longitude", () => {
    expect(earthFacing({ lat: 78.22, lon: 15.65 })).toEqual({ lat: 55, lon: 15.65 });
  });

  test("leans no further than 55 degrees toward the south pole", () => {
    expect(earthFacing({ lat: -90, lon: 0 })).toEqual({ lat: -55, lon: 0 });
  });
});

describe("earthZoom", () => {
  test("fits the Earth to the stage's shorter side at the equator", () => {
    // The Earth fills 0.8 of 640 px, a radius of 256 px, so its circumference is 2π × 256 px.
    expect(earthZoom({ width: 640, height: 900 }, 0)).toBeCloseTo(Math.log2((2 * Math.PI * 256) / 512), 10);
  });

  test("zooms in one level when the stage doubles in size", () => {
    const small = earthZoom({ width: 400, height: 400 }, 20);
    expect(earthZoom({ width: 800, height: 800 }, 20) - small).toBeCloseTo(1, 10);
  });

  test("zooms out toward the poles, where one zoom level draws the globe larger", () => {
    const stage = { width: 800, height: 800 };
    expect(earthZoom(stage, 60) - earthZoom(stage, 0)).toBeCloseTo(-1, 10);
    expect(earthZoom(stage, -60)).toBeCloseTo(earthZoom(stage, 60), 10);
  });

  test("stays finite at a pole", () => {
    const stage = { width: 800, height: 800 };
    expect(Number.isFinite(earthZoom(stage, 90))).toBe(true);
    expect(earthZoom(stage, 90)).toBe(earthZoom(stage, 85));
  });
});

describe("stagePadding", () => {
  test("pads the left of a stage that sits beside the case file", () => {
    const padding = stagePadding(
      { top: 0, left: 600, width: 840, height: 900 },
      { width: 1440, height: 900 },
    );
    expect(padding).toEqual({ top: 0, left: 600, right: 0, bottom: 0 });
  });

  test("pads above and below a stage that sits in the page of a phone", () => {
    const padding = stagePadding(
      { top: 240, left: 12, width: 351, height: 292 },
      { width: 375, height: 812 },
    );
    expect(padding).toEqual({ top: 240, left: 12, right: 12, bottom: 280 });
  });

  test("gives no negative padding when the stage reaches past the viewport", () => {
    const padding = stagePadding({ top: 700, left: 0, width: 400, height: 300 }, { width: 375, height: 812 });
    expect(padding.right).toBe(0);
    expect(padding.bottom).toBe(0);
  });
});

// MapLibre's default camera: this many degrees tall.
const FIELD_OF_VIEW = 36.87;

describe("earthDiscRadius", () => {
  test("is the radius the whole-Earth view draws the disc at, a little under the sphere's", () => {
    // A stage 840px wide gives a sphere of 0.8 x 840 / 2 = 336px; from a camera 1350px away over
    // a viewport 900px high, its disc is 336 x 1350 / sqrt(1350 x (1350 + 672)) px.
    const stage = { width: 840, height: 900 };
    const radius = earthDiscRadius(earthZoom(stage, 18), 18, 900, FIELD_OF_VIEW);
    expect(radius).toBeCloseTo((336 * 1350) / Math.sqrt(1350 * 2022), 0);
    expect(radius).toBeLessThan(336);
  });

  test("is the same at every latitude the whole-Earth view faces", () => {
    const stage = { width: 840, height: 900 };
    const atEquator = earthDiscRadius(earthZoom(stage, 0), 0, 900, FIELD_OF_VIEW);
    expect(earthDiscRadius(earthZoom(stage, 55), 55, 900, FIELD_OF_VIEW)).toBeCloseTo(atEquator, 6);
    expect(earthDiscRadius(earthZoom(stage, -55), -55, 900, FIELD_OF_VIEW)).toBeCloseTo(atEquator, 6);
  });

  test("grows as the view zooms in", () => {
    expect(earthDiscRadius(3, 20, 900, FIELD_OF_VIEW)).toBeGreaterThan(
      earthDiscRadius(2, 20, 900, FIELD_OF_VIEW),
    );
  });

  test("stays finite at a pole", () => {
    expect(earthDiscRadius(1, 90, 900, FIELD_OF_VIEW)).toBe(earthDiscRadius(1, 85, 900, FIELD_OF_VIEW));
  });
});

describe("ringFits", () => {
  test("is true while the Earth and its ring fit the stage's shorter side", () => {
    expect(ringFits(100, { width: 221, height: 600 })).toBe(true);
    expect(ringFits(100, { width: 600, height: 219 })).toBe(false);
  });
});

describe("graticuleFeatures", () => {
  const lines = graticuleFeatures().features.map((feature) => feature.geometry.coordinates);
  const meridians = lines.filter((line) => line.every(([lon]) => lon === line[0]?.[0]));
  const parallels = lines.filter((line) => line.every(([, lat]) => lat === line[0]?.[1]));

  test("draws a meridian every 15 degrees, from 84 degrees south to 84 degrees north", () => {
    expect(meridians.map((line) => line[0]?.[0])).toEqual(
      Array.from({ length: 24 }, (_, index) => -180 + 15 * index),
    );
    for (const line of meridians) {
      expect(line[0]?.[1]).toBe(-84);
      expect(line.at(-1)?.[1]).toBe(84);
    }
  });

  test("draws a parallel every 15 degrees, from 75 degrees south to 75 degrees north, round the Earth", () => {
    expect(parallels.map((line) => line[0]?.[1])).toEqual([-75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75]);
    for (const line of parallels) {
      expect(line[0]?.[0]).toBe(-180);
      expect(line.at(-1)?.[0]).toBe(180);
    }
  });

  test("gives every line a point each 2 degrees, so it bends with the globe", () => {
    expect(lines).toHaveLength(meridians.length + parallels.length);
    for (const line of meridians) expect(line).toHaveLength(85);
    for (const line of parallels) expect(line).toHaveLength(181);
  });
});

describe("isInView", () => {
  // The whole-Earth view on a stage 840px wide: a sphere of 336px seen from 1350px away, so the
  // horizon lies acos(336 / 1686), about 78.5 degrees, round the Earth from the point it faces.
  const zoom = earthZoom({ width: 840, height: 900 }, 0);
  const centre = { lat: 0, lon: 20 };
  const inView = (point: { lat: number; lon: number }): boolean =>
    isInView(centre, point, zoom, 900, FIELD_OF_VIEW);

  test("sees the point the globe faces, and not the point opposite it", () => {
    expect(inView(centre)).toBe(true);
    expect(inView({ lat: 0, lon: -160 })).toBe(false);
  });

  test("sees a point short of the horizon, and not one past it", () => {
    expect(inView({ lat: 0, lon: 20 + 75 })).toBe(true);
    expect(inView({ lat: 0, lon: 20 + 82 })).toBe(false);
    expect(inView({ lat: 75, lon: 20 })).toBe(true);
    expect(inView({ lat: -82, lon: 20 })).toBe(false);
  });

  test("sees further round the Earth from further away", () => {
    const point = { lat: 0, lon: 20 + 82 };
    expect(isInView(centre, point, zoom - 2, 900, FIELD_OF_VIEW)).toBe(true);
  });
});

describe("exampleLinkFeatures", () => {
  const athens = { name: "Athens", lat: 37.98, lon: 23.73 };
  const helsinki = { name: "Helsinki", lat: 60.17, lon: 24.94 };
  const pin = (number: number, places: (typeof athens)[]) => ({
    number,
    title: "A case",
    url: "/case",
    places,
  });

  test("joins the places of a case that tests two, in the case's order", () => {
    const { features } = exampleLinkFeatures([pin(1, [athens]), pin(2, [athens, helsinki])]);
    expect(features.map((feature) => feature.geometry.coordinates)).toEqual([
      [
        [23.73, 37.98],
        [24.94, 60.17],
      ],
    ]);
  });

  test("draws nothing for cases of one place", () => {
    expect(exampleLinkFeatures([pin(1, [athens])]).features).toEqual([]);
  });
});
