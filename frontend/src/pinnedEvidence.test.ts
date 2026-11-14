import { expect, test } from "vitest";
import { buildCaseQuery, buildSeriesQuery, parseCaseQuery } from "./caseUrl";
import { formatPValue } from "./format";

test("case URLs round-trip immutable evidence and precise requested coordinates", () => {
  const params = {
    variable: "air_temp",
    places: [{ lat: 0.249, lon: 0 }],
    from: 1981,
    to: 2025,
    season: "annual" as const,
    snapshotIds: ["a".repeat(64)],
    analysisVersion: "td-2026-11-v1",
  };
  expect(parseCaseQuery(buildCaseQuery(params))).toEqual({ ok: true, value: params });
  expect(buildCaseQuery(params)).toContain("p=0.249,0");
});

test("CSV URLs retain the evidence and analysis version of the viewed case", () => {
  const query = buildSeriesQuery({
    variable: "air_temp",
    place: { lat: 0.249, lon: 0 },
    from: 1981,
    to: 2025,
    season: "annual",
    snapshotIds: ["b".repeat(64)],
    analysisVersion: "td-2026-11-v1",
    resolution: "yearly",
    format: "csv",
  });
  expect(query).toContain(`snap=${"b".repeat(64)}`);
  expect(query).toContain("av=td-2026-11-v1");
});

test("unavailable inference is not formatted as zero or p equals one", () => {
  expect(formatPValue(null)).toBe("Not assessed");
});
