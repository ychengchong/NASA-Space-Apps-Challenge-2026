import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { WorldTrend } from "../api";
import { TrendChart } from "./TrendChart";
import { AIR_TEMP, investigation, placeResult, SIGNIFICANT_RISE } from "./testData";
import { WorldAnswer } from "./WorldView";

const WORLD: WorldTrend = {
  variable: AIR_TEMP,
  requested: { from: 1981, to: 2025, season: "annual" },
  result: {
    ...placeResult({
      kind: "inference_unavailable",
      direction: null,
      sentence:
        "The estimated change in air temperature averaged over a sample of 162 grid points across the whole world is +0.20 °C per decade over 1981-2025. This is an estimate from a sample, and significance has not been assessed.",
      cautions: [],
    }),
  },
  points: 162,
  sample_note:
    "This is an estimate from a sample of 162 grid points, one every 20° of latitude and longitude.",
  steps: ["Used a fixed sample of 162 grid points."],
  sources: [],
  app_url: "/world?v=air_temp&from=1981&to=2025&s=annual",
};

describe("WorldAnswer", () => {
  test("shows the API's verdict sentence and the note on the sample", () => {
    const html = renderToStaticMarkup(<WorldAnswer world={WORLD} />);
    expect(html).toContain("The whole world");
    expect(html).toContain(WORLD.result.verdict.sentence);
    expect(html).toContain(WORLD.sample_note);
  });
});

describe("TrendChart without monthly values", () => {
  test("offers no monthly values for a series no place stands behind", () => {
    const html = renderToStaticMarkup(
      <TrendChart investigation={investigation(SIGNIFICANT_RISE)} monthly={false} />,
    );
    expect(html).not.toContain("Show monthly values");
  });
});
