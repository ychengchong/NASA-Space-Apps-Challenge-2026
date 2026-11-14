import { describe, expect, test } from "vitest";
import { isSeason, SEASON_ORDER, seasonAverageText, seasonLabel } from "./seasons";

describe("seasonLabel", () => {
  test("names every season by its months", () => {
    expect(SEASON_ORDER.map(seasonLabel)).toEqual([
      "Every month",
      "December to February",
      "March to May",
      "June to August",
      "September to November",
    ]);
  });

  test("never uses a hemisphere's season name", () => {
    const labels = SEASON_ORDER.map(seasonLabel).join(" ").toLowerCase();
    for (const word of ["winter", "spring", "summer", "autumn", "fall"]) {
      expect(labels).not.toContain(word);
    }
  });
});

describe("seasonAverageText", () => {
  test("describes the yearly average of every month", () => {
    expect(seasonAverageText("annual")).toBe("the average of all twelve months");
  });

  test("describes the yearly average of a season by its months", () => {
    expect(seasonAverageText("JJA")).toBe("the average of June to August");
  });
});

describe("isSeason", () => {
  test("accepts the season codes of spec 5", () => {
    expect(SEASON_ORDER.every(isSeason)).toBe(true);
  });

  test("rejects a season name that is not a code", () => {
    expect(isSeason("winter")).toBe(false);
  });
});
