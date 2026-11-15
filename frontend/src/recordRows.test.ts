import { describe, expect, test } from "vitest";
import type { Records } from "./api";
import { RECORDS } from "./components/testData";
import { recordRows } from "./recordRows";

const UNITS = { decimals: 2, rate_units: "°C" };

describe("recordRows", () => {
  test("gives the highest and lowest years and the two windows with their change", () => {
    expect(recordRows(RECORDS, UNITS)).toEqual([
      {
        kind: "years",
        label: "Highest",
        items: [
          { year: 2020, value: "8.26" },
          { year: 2025, value: "7.87" },
          { year: 2024, value: "7.68" },
        ],
      },
      {
        kind: "years",
        label: "Lowest",
        items: [
          { year: 1987, value: "2.88" },
          { year: 1985, value: "3.01" },
          { year: 1986, value: "4.18" },
        ],
      },
      {
        kind: "window",
        label: "Ten-year means",
        last: "2016 to 2025: 7.20",
        first: "1981 to 1990: 4.80",
        change: "+2.40 °C",
      },
    ]);
  });

  test("keeps the API's sentence for a list with tied years, which the fields cannot word", () => {
    const tied: Records = { ...RECORDS, lowest_tied: 41 };
    const [, lowest] = recordRows(tied, UNITS);
    expect(lowest).toEqual({ kind: "sentence", label: "Lowest", sentence: RECORDS.sentences[1] });
  });

  test("keeps the API's one sentence when every year has the same value", () => {
    const constant: Records = {
      ...RECORDS,
      highest: [],
      lowest: [],
      sentences: ["Every year used has the same value (°C): 1.00."],
    };
    expect(recordRows(constant, UNITS)).toEqual([
      { kind: "sentence", label: "Every year", sentence: "Every year used has the same value (°C): 1.00." },
    ]);
  });

  test("leaves the window out for fewer than twenty years, as the API does", () => {
    const short: Records = { ...RECORDS, first_ten: null, last_ten: null, change: null };
    expect(recordRows(short, UNITS).map((row) => row.kind)).toEqual(["years", "years"]);
  });

  test("writes a small value with the sentences' extra digits instead of 0.00", () => {
    const small: Records = { ...RECORDS, highest: [{ year: 1985, value: 0.00085 }] };
    const [highest] = recordRows(small, UNITS);
    expect(highest).toMatchObject({ items: [{ year: 1985, value: "0.001" }] });
  });
});
