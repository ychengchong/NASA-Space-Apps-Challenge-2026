import { describe, expect, test } from "vitest";
import {
  isSeason,
  periodText,
  SEASON_ORDER,
  seasonAverageText,
  seasonLabel,
  seasonMonthsText,
} from "./seasons";

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

describe("seasonMonthsText", () => {
  test("says all months for the whole year", () => {
    expect(seasonMonthsText("annual")).toBe("all months");
  });

  test("names a season by its months", () => {
    expect(seasonMonthsText("SON")).toBe("September to November");
  });
});

describe("periodText", () => {
  test("gives the first and last year, then the months", () => {
    expect(periodText({ from: 1981, to: 2025, season: "annual" })).toBe("1981 to 2025, all months");
    expect(periodText({ from: 1991, to: 2020, season: "JJA" })).toBe("1991 to 2020, June to August");
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
