/** Small answers in the shapes of spec 5, for rendering components in tests. */

import type {
  Citation,
  Investigation,
  PlaceResult,
  Records,
  TrendMap,
  VariableSummary,
  Verdict,
} from "../api";

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

/** Record years as the API sends them (spec 7, "Record years"). */
export const RECORDS: Records = {
  highest: [
    { year: 2020, value: 8.26 },
    { year: 2025, value: 7.87 },
    { year: 2024, value: 7.68 },
  ],
  lowest: [
    { year: 1987, value: 2.88 },
    { year: 1985, value: 3.01 },
    { year: 1986, value: 4.18 },
  ],
  highest_tied: 0,
  lowest_tied: 0,
  first_ten: { years: [1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990], mean: 4.8 },
  last_ten: { years: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], mean: 7.2 },
  change: 2.4,
  sentences: [
    "Highest yearly values used (°C): 8.26 in 2020, 7.87 in 2025 and 7.68 in 2024.",
    "Lowest yearly values used (°C): 2.88 in 1987, 3.01 in 1985 and 4.18 in 1986.",
    "The mean of the last ten years used, 2016 to 2025, was 2.40 °C higher than the mean of the first ten, 1981 to 1990.",
  ],
  note: "These facts describe the yearly values used. They are not tests, and their significance was not assessed.",
};

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

/** A citation as the server builds it from the reviewed manifest (spec 5, "Citation"). */
export const CITATION: Citation = {
  source_id: "power-sources-meteorology",
  section_id: "power-sources-meteorology-01",
  title: "POWER Meteorological Data Sources",
  publisher: "NASA Langley Research Center, POWER Project",
  url: "https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/",
  section: "POWER Meteorological Data Sources: MERRA-2",
  kind: "agency",
  passage: "Meteorological parameters come from the MERRA-2 reanalysis.",
};

/** One of the project's own notes, which the corpus marks apart from agency sources. */
export const PROJECT_CITATION: Citation = {
  source_id: "project-sen-slope",
  section_id: "project-sen-slope-01",
  title: "Sen's slope and the total change",
  publisher: "Trend Detective project",
  url: "https://github.com/example/trend-detective/blob/main/backend/data/corpus/project/sen-slope.md",
  section: "Sen's slope and the total change",
  kind: "project",
  passage: "Sen's slope is the median of the slopes between every pair of years.",
};
