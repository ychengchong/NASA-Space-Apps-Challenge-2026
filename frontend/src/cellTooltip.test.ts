import { describe, expect, test } from "vitest";
import { cellTooltipLines } from "./cellTooltip";
import { AIR_TEMP } from "./components/testData";

describe("cellTooltipLines", () => {
  test("names the grid point, the rate and the p-value of a cell with a result", () => {
    const lines = cellTooltipLines(
      { lat: 60.5, lon: 24.375, sen_slope: 0.51, mk_p: 0.012, significant: false },
      AIR_TEMP,
    );
    expect(lines).toEqual([
      "60.5°N, 24.4°E",
      "+0.51 °C per decade",
      "p = 0.012",
      "Click to open this cell as a case.",
    ]);
  });

  test("says when a cell passes the map's stricter test", () => {
    const lines = cellTooltipLines(
      { lat: 60.5, lon: 24.375, sen_slope: 0.51, mk_p: 0.0001, significant: true },
      AIR_TEMP,
    );
    expect(lines).toContain("p < 0.001");
    expect(lines).toContain("Marked: passes the map's stricter test.");
  });

  test("gives the reason instead of numbers for a cell without a result", () => {
    const lines = cellTooltipLines(
      { lat: 60.5, lon: 24.375, sen_slope: null, mk_p: null, significant: false },
      AIR_TEMP,
    );
    expect(lines).toEqual([
      "60.5°N, 24.4°E",
      "No result: too few complete years to test.",
      "Click to open this cell as a case.",
    ]);
  });
});
