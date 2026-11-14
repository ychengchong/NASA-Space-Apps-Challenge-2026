import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { OverviewRow, PlaceOverview } from "../api";
import { OverviewAnswer } from "./PlaceOverviewView";
import { AIR_TEMP } from "./testData";

function row(id: string, name: string, theme: string, sentence: string): OverviewRow {
  return {
    variable: { ...AIR_TEMP, id, name, theme },
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
    sentence,
  };
}

const OVERVIEW: PlaceOverview = {
  name: "Helsinki",
  lat: 60.17,
  lon: 24.94,
  requested: { from: 1981, to: 2025, season: "annual" },
  rows: [
    row(
      "air_temp",
      "Air temperature",
      "temperature",
      "+0.58 °C per decade. The trend test finds it significant.",
    ),
    row("precipitation", "Precipitation", "water", "-0.04 mm/day per decade. Significance was not assessed."),
  ],
  note: "This view cannot say which of these changes are real.",
  sources: [],
  app_url: "/place?p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual",
};

describe("OverviewAnswer", () => {
  const html = renderToStaticMarkup(<OverviewAnswer overview={OVERVIEW} onOpenPage={() => undefined} />);

  test("asks what is changing at the place and shows the API's fixed note", () => {
    expect(html).toContain("What is changing in Helsinki?");
    expect(html).toContain(OVERVIEW.note);
  });

  test("groups the variables under their themes, each line with the API's sentence", () => {
    expect(html).toContain(">Temperature</h2>");
    expect(html).toContain(">Water</h2>");
    for (const item of OVERVIEW.rows) expect(html).toContain(item.sentence);
  });

  test("links each variable to its ordinary case at the place", () => {
    expect(html).toContain(
      'href="/case?v=precipitation&amp;p=60.17,24.94&amp;label=Helsinki&amp;from=1981&amp;to=2025&amp;s=annual"',
    );
  });

  test("shows the API's variable and source cautions beside the row", () => {
    const caution = "The source changes in 2001, which can create an artificial step.";
    const overview = {
      ...OVERVIEW,
      rows: [{ ...OVERVIEW.rows[0]!, caution_sentences: [caution] }],
    };

    const html = renderToStaticMarkup(<OverviewAnswer overview={overview} onOpenPage={() => undefined} />);

    expect(html).toContain(caution);
    expect(html).toContain("Caution:");
  });
});
