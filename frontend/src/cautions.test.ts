import { describe, expect, test } from "vitest";
import type { Trend, VariableSummary } from "./api";
import { cautionText, cautionTexts, crossedSourceChanges, joinWords } from "./cautions";

const AIR_TEMPERATURE: VariableSummary = {
  id: "air_temp",
  name: "Air temperature",
  definition: "How warm the air is two metres above the ground, averaged over the month.",
  units: "°C",
  rate_units: "°C",
  decimals: 2,
  theme: "temperature",
  record_start: 1981,
  related: [],
  region_types: [],
};

const PRECIPITATION: VariableSummary = {
  ...AIR_TEMPERATURE,
  id: "precipitation",
  name: "Precipitation",
  trend_note: "Rainfall trends from this model are less reliable than temperature trends.",
};

const SUNLIGHT: VariableSummary = {
  ...AIR_TEMPERATURE,
  id: "sunlight",
  name: "Sunlight reaching the surface",
  record_start: 1984,
  source_changes: [2001],
};

function trendOver(firstYear: number, lastYear: number): Trend {
  return {
    n: lastYear - firstYear + 1,
    first_year: firstYear,
    last_year: lastYear,
    sen_slope: 0.3,
    sen_ci95: [0.1, 0.5],
    line: [5, 6],
    total_change: 1,
    mk_p: 0.01,
    lag1: 0.1,
    variance_factor: 1.2,
    ols_slope: 0.3,
    ols_p: 0.01,
  };
}

describe("cautionText", () => {
  test("uses the spec 7 wording for a short record", () => {
    expect(cautionText("short_record", AIR_TEMPERATURE, trendOver(2000, 2015))).toBe(
      "This record is short. Trends in short records often fade as more years arrive.",
    );
  });

  test("uses the spec 7 wording for year-to-year memory", () => {
    expect(cautionText("autocorrelated", AIR_TEMPERATURE, trendOver(1981, 2025))).toBe(
      "Each year here resembles the one before. The test allows for that, which makes it harder to pass.",
    );
  });

  test("uses the spec 7 wording when the methods disagree", () => {
    expect(cautionText("methods_disagree", AIR_TEMPERATURE, trendOver(1981, 2025))).toBe(
      "Two standard methods disagree about this trend.",
    );
  });

  test("uses the spec 7 wording for a borderline result", () => {
    expect(cautionText("borderline", AIR_TEMPERATURE, trendOver(1981, 2025))).toBe(
      "This result is close to the threshold for significance.",
    );
  });

  test("shows the variable's own trend note", () => {
    expect(cautionText("variable_note", PRECIPITATION, null)).toBe(
      "Rainfall trends from this model are less reliable than temperature trends.",
    );
  });

  test("has no text for a trend note the variable lacks", () => {
    expect(cautionText("variable_note", AIR_TEMPERATURE, null)).toBeNull();
  });

  test("names the year in which the source changes", () => {
    expect(cautionText("source_change", SUNLIGHT, trendOver(1984, 2025))).toBe(
      "The data source for this variable changes in 2001, which can create an artificial step.",
    );
  });

  test("names only the change years the trend crosses", () => {
    const variable = { ...SUNLIGHT, source_changes: [1990, 2001, 2030] };
    expect(cautionText("source_change", variable, trendOver(1995, 2025))).toBe(
      "The data source for this variable changes in 2001, which can create an artificial step.",
    );
  });

  test("joins several crossed change years", () => {
    const variable = { ...SUNLIGHT, source_changes: [1995, 2001] };
    expect(cautionText("source_change", variable, trendOver(1984, 2025))).toBe(
      "The data source for this variable changes in 1995 and 2001, which can create an artificial step.",
    );
  });
});

describe("crossedSourceChanges", () => {
  test("counts a change in the last year used", () => {
    expect(crossedSourceChanges(SUNLIGHT, { first_year: 1984, last_year: 2001 })).toEqual([2001]);
  });

  test("does not count a change in the first year used", () => {
    expect(crossedSourceChanges(SUNLIGHT, { first_year: 2001, last_year: 2025 })).toEqual([]);
  });

  test("does not count a change after the last year used", () => {
    expect(crossedSourceChanges(SUNLIGHT, { first_year: 1984, last_year: 2000 })).toEqual([]);
  });

  test("finds nothing for a variable without source changes", () => {
    expect(crossedSourceChanges(AIR_TEMPERATURE, { first_year: 1981, last_year: 2025 })).toEqual([]);
  });
});

describe("cautionTexts", () => {
  test("keeps the order of the cautions, most important first", () => {
    const texts = cautionTexts(["variable_note", "short_record"], PRECIPITATION, trendOver(2010, 2025));
    expect(texts).toEqual([
      "Rainfall trends from this model are less reliable than temperature trends.",
      "This record is short. Trends in short records often fade as more years arrive.",
    ]);
  });

  test("skips a caution that has no text", () => {
    expect(cautionTexts(["variable_note", "borderline"], AIR_TEMPERATURE, null)).toEqual([
      "This result is close to the threshold for significance.",
    ]);
  });
});

describe("joinWords", () => {
  test("joins words as the backend does", () => {
    expect(joinWords([])).toBe("");
    expect(joinWords(["A"])).toBe("A");
    expect(joinWords(["A", "B"])).toBe("A and B");
    expect(joinWords(["A", "B", "C"])).toBe("A, B and C");
  });
});
