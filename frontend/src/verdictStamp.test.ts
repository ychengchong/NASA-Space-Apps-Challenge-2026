import { describe, expect, test } from "vitest";
import type { Verdict } from "./api";
import { investigation, placeResult, SIGNIFICANT_RISE } from "./components/testData";
import { verdictLine, verdictTone } from "./verdictStamp";

const NOT_SIGNIFICANT_FALL: Verdict = {
  kind: "not_significant",
  direction: "falling",
  sentence: "Air temperature in Helsinki has no significant trend from 1981 to 2025.",
  cautions: [],
};

const TOO_FEW_YEARS: Verdict = {
  kind: "too_few_years",
  direction: null,
  sentence: "There are too few years to test a trend.",
  cautions: [],
};

describe("verdictLine", () => {
  test("gives one significant place the card's figure and stamp words, without its name", () => {
    expect(verdictLine(investigation(SIGNIFICANT_RISE))).toEqual([
      {
        index: 0,
        name: null,
        figure: "+0.05 °C per decade",
        direction: { arrow: "↑", word: "Rising", tone: "rising" },
        kind: "Significant",
        ink: "rising",
      },
    ]);
  });

  test("names a place that is not significant and gives it no figure, as the card does", () => {
    const [entry] = verdictLine(investigation(NOT_SIGNIFICANT_FALL));
    expect(entry?.name).toBe("Helsinki");
    expect(entry?.figure).toBeNull();
    expect(entry?.direction?.word).toBe("Falling");
    expect(entry?.kind).toBe("Not significant");
    expect(entry?.ink).toBe("faded");
  });

  test("stamps a verdict without a direction with its kind alone", () => {
    const [entry] = verdictLine(investigation(TOO_FEW_YEARS));
    expect(entry?.direction).toBeNull();
    expect(entry?.kind).toBe("Too few years");
  });

  test("names every place of a comparison, in order, each with its own figure rule", () => {
    const athens = placeResult(SIGNIFICANT_RISE);
    athens.place = { ...athens.place, name: "Athens" };
    const both = { ...investigation(SIGNIFICANT_RISE), results: [athens, placeResult(NOT_SIGNIFICANT_FALL)] };
    const entries = verdictLine(both);
    expect(entries.map((entry) => [entry.index, entry.name, entry.figure])).toEqual([
      [0, "Athens", "+0.05 °C per decade"],
      [1, "Helsinki", null],
    ]);
  });
});

describe("verdictTone", () => {
  test("colours the case file rising when every place rises significantly", () => {
    expect(verdictTone(investigation(SIGNIFICANT_RISE))).toBe("rising");
  });

  test("colours it falling when every place falls significantly", () => {
    expect(verdictTone(investigation({ ...SIGNIFICANT_RISE, direction: "falling" }))).toBe("falling");
  });

  test("keeps it plain for a verdict that is not significant", () => {
    expect(verdictTone(investigation(NOT_SIGNIFICANT_FALL))).toBe("plain");
  });

  test("keeps it plain when the places of a comparison disagree", () => {
    const both = {
      ...investigation(SIGNIFICANT_RISE),
      results: [placeResult(SIGNIFICANT_RISE), placeResult({ ...SIGNIFICANT_RISE, direction: "falling" })],
    };
    expect(verdictTone(both)).toBe("plain");
  });
});
