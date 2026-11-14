import { describe, expect, test } from "vitest";
import type { SeasonRate, SeasonRates } from "./api";
import { chartDescription, significanceText, yearsText } from "./seasonRows";
import { AIR_TEMP, placeResult, SIGNIFICANT_RISE } from "./components/testData";

const ROW: SeasonRate = {
  season: "DJF",
  n: 44,
  first_year: 1982,
  last_year: 2025,
  sen_slope: 1.48,
  total_change: 6.4,
  verdict_kind: "inference_unavailable",
  assessed: false,
  sentence: "December to February: +1.48 °C per decade from 1982 to 2025, over 44 complete years.",
};

describe("yearsText", () => {
  test("names the first and last year used and how many", () => {
    expect(yearsText(ROW)).toBe("1982 to 2025 (44)");
  });

  test("says none for a season without a complete year", () => {
    expect(yearsText({ ...ROW, n: 0, first_year: null, last_year: null })).toBe("None");
  });
});

describe("significanceText", () => {
  test("says a descriptive rate was not assessed", () => {
    expect(significanceText(ROW)).toBe("Not assessed");
  });

  test("names the verdict only for a row the API marks as assessed", () => {
    expect(significanceText({ ...ROW, season: "annual", assessed: true, verdict_kind: "significant" })).toBe(
      "Significant, from the trend test",
    );
    expect(significanceText({ ...ROW, assessed: false, verdict_kind: "significant" })).toBe("Not assessed");
  });

  test("says too few years or no data for a row without a rate", () => {
    expect(significanceText({ ...ROW, verdict_kind: "too_few_years", sen_slope: null })).toBe(
      "Too few years",
    );
    expect(significanceText({ ...ROW, verdict_kind: "no_data", sen_slope: null })).toBe("No data");
  });
});

describe("chartDescription", () => {
  test("names each place before its rows' sentences", () => {
    const place = placeResult(SIGNIFICANT_RISE).place;
    const answer: SeasonRates = {
      variable: AIR_TEMP,
      requested: { from: 1981, to: 2025, season: "annual" },
      places: [
        { place, rates: [ROW] },
        { place: { ...place, name: "Nairobi" }, rates: [ROW] },
      ],
      note: "Each rate is descriptive.",
    };
    expect(chartDescription(answer)).toBe(`Helsinki: ${ROW.sentence} Nairobi: ${ROW.sentence}`);
  });
});
