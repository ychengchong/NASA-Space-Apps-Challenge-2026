import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { Gap, Investigation } from "../api";
import { GapChart } from "./GapChart";
import { investigation, SIGNIFICANT_RISE } from "./testData";
import { VerdictCard } from "./VerdictCard";

const GAP: Gap = {
  first_place: "Athens",
  second_place: "Helsinki",
  series: [
    { year: 1981, value: -1.0 },
    { year: 1982, value: -0.9 },
  ],
  n: 45,
  first_year: 1981,
  last_year: 2025,
  sen_slope: 0.12,
  total_change: 0.54,
  line: [-1.0, -0.46],
  same_cell: false,
  sentence:
    "The difference between Athens and Helsinki, Athens minus Helsinki, changed by about +0.12 mm/day per decade from 1981 to 2025, over 45 common years.",
};

function withGap(gap: Gap | null): Investigation {
  return { ...investigation(SIGNIFICANT_RISE), gap };
}

describe("GapChart", () => {
  test("names the two places in order and gives the API's sentence as the chart's text", () => {
    const html = renderToStaticMarkup(<GapChart investigation={withGap(GAP)} />);
    expect(html).toContain("The gap: Athens minus Helsinki");
    expect(html).toContain(GAP.sentence);
  });

  test("draws nothing without a gap or for places in one grid cell", () => {
    expect(renderToStaticMarkup(<GapChart investigation={withGap(null)} />)).toBe("");
    expect(renderToStaticMarkup(<GapChart investigation={withGap({ ...GAP, same_cell: true })} />)).toBe("");
  });
});

describe("VerdictCard with a gap", () => {
  test("adds the gap's sentence after the comparison's summary, which stays as it is", () => {
    const summary = "Descriptive comparison on 45 identical complete years.";
    const html = renderToStaticMarkup(<VerdictCard investigation={{ ...withGap(GAP), summary }} />);
    expect(html).toContain(summary);
    expect(html.indexOf(GAP.sentence)).toBeGreaterThan(html.indexOf(summary));
  });
});
