import { describe, expect, test } from "vitest";
import { boxAroundPlace, boxCorners, boxFromDrag, cellBounds, gridSteps } from "./regionBox";

describe("boxAroundPlace", () => {
  test("centres a 10 by 10 degree box on the place's nearest whole degrees", () => {
    expect(boxAroundPlace({ lat: 60.17, lon: 24.94 })).toEqual({ south: 55, west: 20, north: 65, east: 30 });
  });

  test("keeps the place inside the box", () => {
    const place = { lat: -1.29, lon: 36.82 };
    const box = boxAroundPlace(place);
    expect(box.south).toBeLessThanOrEqual(place.lat);
    expect(box.north).toBeGreaterThanOrEqual(place.lat);
    expect(box.west).toBeLessThanOrEqual(place.lon);
    expect(box.east).toBeGreaterThanOrEqual(place.lon);
  });

  test("gives sides of exactly 10 degrees, even where decimals would add float noise", () => {
    const box = boxAroundPlace({ lat: 40.71, lon: -68.98 });
    expect(box.north - box.south).toBe(10);
    expect(box.east - box.west).toBe(10);
  });

  test("moves the box south of the North Pole instead of past it", () => {
    expect(boxAroundPlace({ lat: 88.5, lon: 0 })).toEqual({ south: 80, west: -5, north: 90, east: 5 });
  });

  test("moves the box north of the South Pole instead of past it", () => {
    expect(boxAroundPlace({ lat: -89, lon: 0 })).toEqual({ south: -90, west: -5, north: -80, east: 5 });
  });

  test("moves the box west of the 180 degree meridian instead of across it", () => {
    expect(boxAroundPlace({ lat: -17.7, lon: 178.4 })).toEqual({
      south: -23,
      west: 170,
      north: -13,
      east: 180,
    });
  });

  test("moves the box east of the -180 degree meridian instead of across it", () => {
    expect(boxAroundPlace({ lat: 0, lon: -179.9 })).toEqual({ south: -5, west: -180, north: 5, east: -170 });
  });
});

describe("boxFromDrag", () => {
  test("widens a drag to whole degrees in either direction", () => {
    expect(boxFromDrag({ lat: 62.4, lon: 27.2 }, { lat: 57.6, lon: 21.9 })).toEqual({
      south: 57,
      west: 21,
      north: 63,
      east: 28,
    });
  });

  test("cuts a long drag to 10 degrees from the corner where it started", () => {
    expect(boxFromDrag({ lat: 40.2, lon: 10.5 }, { lat: 60.3, lon: 12.5 })).toEqual({
      south: 40,
      west: 10,
      north: 50,
      east: 13,
    });
    expect(boxFromDrag({ lat: 60.3, lon: 12.5 }, { lat: 40.2, lon: -10 })).toEqual({
      south: 51,
      west: 3,
      north: 61,
      east: 13,
    });
  });

  test("keeps a drag inside the globe", () => {
    expect(boxFromDrag({ lat: 86.5, lon: 175.5 }, { lat: 91.2, lon: 183.7 })).toEqual({
      south: 86,
      west: 175,
      north: 90,
      east: 180,
    });
  });
});

describe("gridSteps", () => {
  test("finds the 0.5 by 0.625 degree MERRA-2 grid", () => {
    const cells = [
      { lat: 55, lon: 20 },
      { lat: 55, lon: 20.625 },
      { lat: 55.5, lon: 20 },
      { lat: 55.5, lon: 20.625 },
    ];
    expect(gridSteps(cells)).toEqual({ height: 0.5, width: 0.625 });
  });

  test("finds the 1 degree cells of sunlight and cloud", () => {
    const cells = [
      { lat: 55.5, lon: 20.5 },
      { lat: 55.5, lon: 21.5 },
      { lat: 56.5, lon: 20.5 },
    ];
    expect(gridSteps(cells)).toEqual({ height: 1, width: 1 });
  });

  test("falls back to the MERRA-2 step for a single row or column", () => {
    expect(gridSteps([{ lat: 10, lon: 5 }])).toEqual({ height: 0.5, width: 0.625 });
  });

  test("drops float noise from the gaps", () => {
    const cells = [
      { lat: 0.1, lon: 0 },
      { lat: 0.6, lon: 0.3 },
    ];
    expect(gridSteps(cells)).toEqual({ height: 0.5, width: 0.3 });
  });
});

describe("cellBounds", () => {
  test("centres the cell's rectangle on its grid point", () => {
    expect(cellBounds({ lat: 60, lon: 25 }, { height: 0.5, width: 0.625 })).toEqual([
      [59.75, 24.6875],
      [60.25, 25.3125],
    ]);
  });
});

describe("boxCorners", () => {
  test("gives the south-west and north-east corners", () => {
    expect(boxCorners({ south: 55, west: 20, north: 65, east: 30 })).toEqual([
      [55, 20],
      [65, 30],
    ]);
  });
});
