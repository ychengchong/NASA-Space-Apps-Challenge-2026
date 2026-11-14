import { describe, expect, test } from "vitest";
import { isSignificant, yearRuns } from "./periodScan";

describe("isSignificant", () => {
  test("marks a start year whose p-value is below 0.05", () => {
    expect(isSignificant({ start: 1990, sen_slope: 0.3, mk_p: 0.049 })).toBe(true);
  });

  test("does not mark a p-value of exactly 0.05", () => {
    expect(isSignificant({ start: 1990, sen_slope: 0.3, mk_p: 0.05 })).toBe(false);
  });

  test("does not mark a zero slope, even with p below 0.05", () => {
    expect(isSignificant({ start: 1985, sen_slope: 0, mk_p: 0.03 })).toBe(false);
  });

  test("marks a falling trend whose p-value is below 0.05", () => {
    expect(isSignificant({ start: 1990, sen_slope: -0.3, mk_p: 0.01 })).toBe(true);
  });
});

describe("yearRuns", () => {
  test("writes consecutive years as a run", () => {
    expect(yearRuns([1981, 1982, 1983, 1990])).toBe("1981 to 1983 and 1990");
  });

  test("sorts the years first", () => {
    expect(yearRuns([1990, 1981, 1982])).toBe("1981 to 1982 and 1990");
  });

  test("writes a single year alone", () => {
    expect(yearRuns([2001])).toBe("2001");
  });
});
