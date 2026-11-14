import { describe, expect, test } from "vitest";
import { legendEntry } from "./chartLegend";

describe("legendEntry", () => {
  test("names each kind of mark for one place, without repeating the place", () => {
    expect(legendEntry("Longyearbyen", "yearly values", 1)).toEqual({
      name: "Yearly values",
      showlegend: true,
    });
    expect(legendEntry("Longyearbyen", "trend line", 1)).toEqual({ name: "Trend line", showlegend: true });
  });

  test("names only the places in a comparison, so the legend stays on one row", () => {
    expect(legendEntry("Athens", "yearly values", 2)).toEqual({ name: "Athens", showlegend: true });
    expect(legendEntry("Athens", "record years", 2)).toEqual({
      name: "Athens: record years",
      showlegend: false,
    });
    expect(legendEntry("Athens", "trend line", 2).showlegend).toBe(false);
  });
});
