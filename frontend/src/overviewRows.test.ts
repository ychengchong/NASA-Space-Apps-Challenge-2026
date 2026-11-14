import { describe, expect, test } from "vitest";
import type { OverviewRow, PlaceOverview } from "./api";
import { overviewThemes, rowCaseUrl } from "./overviewRows";
import { AIR_TEMP } from "./components/testData";

function row(id: string, theme: string, recordStart = 1981): OverviewRow {
  return {
    variable: { ...AIR_TEMP, id, theme, record_start: recordStart },
    cell: { lat: 60, lon: 25, height: 0.5, width: 0.625 },
    n: 45,
    first_year: 1981,
    last_year: 2025,
    sen_slope: 0.5,
    total_change: 2.2,
    verdict_kind: "inference_unavailable",
    assessed: false,
    highest_year: 2020,
    lowest_year: 1987,
    sentence: "+0.50 per decade.",
  };
}

const OVERVIEW: PlaceOverview = {
  name: "Helsinki",
  lat: 60.17,
  lon: 24.94,
  requested: { from: 1981, to: 2025, season: "annual" },
  rows: [
    row("air_temp", "temperature"),
    row("precipitation", "water"),
    row("max_temp", "temperature"),
    row("haze", "air", 2001),
  ],
  note: "This view cannot say which of these changes are real.",
  sources: [],
  app_url: "/place?p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual",
};

describe("overviewThemes", () => {
  test("groups rows by theme in order of first appearance, keeping the API's order within each", () => {
    const themes = overviewThemes(OVERVIEW.rows);
    expect(themes.map((group) => group.theme)).toEqual(["temperature", "water", "air"]);
    expect(themes[0]?.rows.map((r) => r.variable.id)).toEqual(["air_temp", "max_temp"]);
  });

  test("never reorders rows by their rate", () => {
    const rows = [
      { ...row("a", "t"), sen_slope: -5 },
      { ...row("b", "t"), sen_slope: 9 },
    ];
    expect(overviewThemes(rows)[0]?.rows.map((r) => r.variable.id)).toEqual(["a", "b"]);
  });
});

describe("rowCaseUrl", () => {
  test("opens the row's variable as a case at the place over the overview's period", () => {
    expect(rowCaseUrl(row("air_temp", "temperature"), OVERVIEW)).toBe(
      "/case?v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual",
    );
  });

  test("starts a variable with a later record at its record's start", () => {
    expect(rowCaseUrl(row("haze", "air", 2001), OVERVIEW)).toContain("from=2001&to=2025");
  });
});
