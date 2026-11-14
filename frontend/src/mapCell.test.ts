import { describe, expect, test } from "vitest";
import {
  cellOutline,
  MERRA2_CELL_HEIGHT,
  MERRA2_CELL_WIDTH,
  placeCellOutline,
  placesExtent,
} from "./mapCell";

describe("cellOutline", () => {
  test("outlines a cell of the MERRA-2 grid around its grid point", () => {
    const cell = { lat: 60, lon: 25, height: MERRA2_CELL_HEIGHT, width: MERRA2_CELL_WIDTH };
    expect(cellOutline(cell)).toEqual([
      [59.75, 24.6875],
      [60.25, 25.3125],
    ]);
  });

  test("outlines a 1 degree cell of sunlight and cloud between whole degrees", () => {
    expect(cellOutline({ lat: 60.5, lon: 24.5, height: 1, width: 1 })).toEqual([
      [60, 24],
      [61, 25],
    ]);
  });

  test("outlines a 1 degree cell south of the equator and west of Greenwich", () => {
    expect(cellOutline({ lat: -22.5, lon: -44.5, height: 1, width: 1 })).toEqual([
      [-23, -45],
      [-22, -44],
    ]);
  });
});

describe("placeCellOutline", () => {
  test("is absent for a place without a cell", () => {
    expect(placeCellOutline({ lat: 60.17, lon: 24.94 })).toBeUndefined();
  });

  test("moves a cell across the antimeridian to the side of its place", () => {
    const cell = { lat: 79, lon: -180, height: MERRA2_CELL_HEIGHT, width: MERRA2_CELL_WIDTH };
    expect(placeCellOutline({ lat: 79, lon: 179.8, cell })).toEqual([
      [78.75, 179.6875],
      [79.25, 180.3125],
    ]);
  });
});

describe("placesExtent", () => {
  test("is absent when there are no places", () => {
    expect(placesExtent([])).toBeUndefined();
  });

  test("is the point itself for a place without a cell", () => {
    expect(placesExtent([{ lat: 60.17, lon: 24.94 }])).toEqual([
      [60.17, 24.94],
      [60.17, 24.94],
    ]);
  });

  test("reaches the far edge of a 1 degree cell that is not centred on its place", () => {
    const cell = { lat: 78.5, lon: 15.5, height: 1, width: 1 };
    expect(placesExtent([{ lat: 78.22, lon: 15.65, cell }])).toEqual([
      [78, 15],
      [79, 16],
    ]);
  });

  test("holds every place and its cell", () => {
    const helsinki = { lat: 60.17, lon: 24.94, cell: { lat: 60.5, lon: 24.5, height: 1, width: 1 } };
    const tallinn = { lat: 59.44, lon: 24.75, cell: { lat: 59.5, lon: 24.5, height: 1, width: 1 } };
    expect(placesExtent([helsinki, tallinn])).toEqual([
      [59, 24],
      [61, 25],
    ]);
  });

  test("stays narrow for a place just west of the antimeridian whose cell is centred on 180 degrees west", () => {
    const cell = { lat: 79, lon: -180, height: MERRA2_CELL_HEIGHT, width: MERRA2_CELL_WIDTH };
    expect(placesExtent([{ lat: 79, lon: 179.8, cell }])).toEqual([
      [78.75, 179.6875],
      [79.25, 180.3125],
    ]);
  });
});
