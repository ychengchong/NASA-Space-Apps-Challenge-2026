import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { SeasonRate, SeasonRates } from "../api";
import { SeasonsPanel, SeasonsView } from "./SeasonsPanel";
import { AIR_TEMP, investigation, placeResult, SIGNIFICANT_RISE } from "./testData";

function rate(season: SeasonRate["season"], assessed: boolean): SeasonRate {
  return {
    season,
    n: 45,
    first_year: 1981,
    last_year: 2025,
    sen_slope: 0.5,
    total_change: 2.2,
    verdict_kind: assessed ? "significant" : "inference_unavailable",
    assessed,
    sentence: `${season}: +0.50 °C per decade from 1981 to 2025, over 45 complete years.`,
  };
}

const ANSWER: SeasonRates = {
  variable: AIR_TEMP,
  requested: { from: 1981, to: 2025, season: "annual" },
  places: [
    {
      place: placeResult(SIGNIFICANT_RISE).place,
      rates: [
        rate("annual", true),
        rate("DJF", false),
        rate("MAM", false),
        rate("JJA", false),
        rate("SON", false),
      ],
    },
  ],
  note: "Each rate is descriptive. Rates for different seasons can differ by chance alone, and no difference between seasons was tested.",
};

function renderView(current: SeasonRate["season"] = "annual"): string {
  return renderToStaticMarkup(
    <SeasonsView
      answer={ANSWER}
      current={current}
      seasonUrl={(season) => `/case?s=${season}`}
      onOpenPage={() => undefined}
    />,
  );
}

describe("SeasonsPanel", () => {
  test("is folded until opened, so it asks the API for nothing", () => {
    const html = renderToStaticMarkup(
      <SeasonsPanel
        params={{ variable: "air_temp", places: [{ lat: 60.17, lon: 24.94 }], season: "annual" }}
        investigation={investigation(SIGNIFICANT_RISE)}
        onOpenPage={() => undefined}
      />,
    );
    expect(html).toContain("Compare the seasons");
    expect(html).not.toContain("Estimating");
  });
});

describe("SeasonsView", () => {
  test("shows the API's note and every row's sentence as given", () => {
    const html = renderView();
    expect(html).toContain(ANSWER.note);
    for (const row of ANSWER.places[0]?.rates ?? []) expect(html).toContain(row.sentence);
  });

  test("names the test's verdict only on the assessed row and says the others were not assessed", () => {
    const html = renderView();
    expect(html.match(/Significant, from the trend test/g)).toHaveLength(1);
    expect(html.match(/Not assessed/g)).toHaveLength(4);
  });

  test("links every other season as a case and marks the case on screen", () => {
    const html = renderView("JJA");
    expect(html).toContain("This case");
    expect(html).toContain('href="/case?s=DJF"');
    expect(html).not.toContain('href="/case?s=JJA"');
  });
});
