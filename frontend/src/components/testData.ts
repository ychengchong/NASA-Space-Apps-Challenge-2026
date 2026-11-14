/** Small answers in the shapes of spec 5, for rendering components in tests. */

import type { Investigation, PlaceResult, TrendMap, VariableSummary, Verdict } from "../api";

export const AIR_TEMP: VariableSummary = {
  id: "air_temp",
  name: "Air temperature",
  definition: "How warm the air is two metres above the ground.",
  units: "°C",
  rate_units: "°C",
  decimals: 2,
  theme: "temperature",
  record_start: 1981,
  related: [],
  region_types: [],
};

export function placeResult(verdict: Verdict): PlaceResult {
  return {
    place: {
      name: "Helsinki",
      lat: 60.17,
      lon: 24.94,
      cell: { lat: 60, lon: 25, height: 0.5, width: 0.625 },
    },
    series: [{ year: 1981, value: 4.5 }],
    trend: {
      n: 45,
      first_year: 1981,
      last_year: 2025,
      sen_slope: 0.05,
      sen_ci95: [0.03, 0.07],
      line: [4, 0.05],
      total_change: 2.2,
      mk_p: 0.001,
      lag1: 0.1,
      variance_factor: 1.1,
      ols_slope: 0.05,
      ols_p: 0.001,
    },
    verdict,
  };
}

export const SIGNIFICANT_RISE: Verdict = {
  kind: "significant",
  direction: "rising",
  sentence: "Air temperature in Helsinki has risen by about 0.50 °C per decade from 1981 to 2025.",
  cautions: [],
};

export function investigation(verdict: Verdict): Investigation {
  return {
    id: "abc123",
    variable: AIR_TEMP,
    requested: { from: 1981, to: 2025, season: "annual" },
    results: [placeResult(verdict)],
    steps: ["Fetched the monthly values."],
    sources: [{ name: "NASA POWER", version: "v2", accessed: "2026-11-01" }],
    app_url: "/case?v=air_temp&p=60.17,24.94",
  };
}

export const TREND_MAP: TrendMap = {
  variable: AIR_TEMP,
  requested: { from: 1981, to: 2025, season: "annual" },
  box: { south: 55, west: 20, north: 65, east: 30 },
  cells: [{ lat: 60, lon: 25, sen_slope: 0.5, mk_p: 0.001, significant: true }],
  area_mean: placeResult(SIGNIFICANT_RISE),
  steps: ["Fetched every grid cell."],
  sources: [{ name: "NASA POWER", version: "v2", accessed: "2026-11-01" }],
  app_url: "/map?v=air_temp&box=55,20,65,30",
};
