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

  test("says no rate is available for a cell without a rate", () => {
    const lines = cellTooltipLines(
      { lat: 60.5, lon: 24.375, sen_slope: null, mk_p: null, significant: false },
      AIR_TEMP,
    );
    expect(lines).toEqual([
      "60.5°N, 24.4°E",
      "No descriptive rate is available.",
      "Click to open this cell as a case.",
    ]);
  });

  test("shows the rate but says significance was not assessed for a cell without a p-value", () => {
    const lines = cellTooltipLines(
      { lat: 60.5, lon: 24.375, sen_slope: 0.51, mk_p: null, significant: false },
      AIR_TEMP,
    );
    expect(lines).toEqual([
      "60.5°N, 24.4°E",
      "+0.51 °C per decade",
      "Significance not assessed for the map.",
      "Click to open this cell as a case.",
    ]);
  });
});
