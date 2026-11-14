import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { Investigation } from "../api";
import { StageCaption } from "./StageCaption";
import { investigation, placeResult, SIGNIFICANT_RISE } from "./testData";

describe("StageCaption", () => {
  test("names the variable, the place with its coordinates, and the period", () => {
    const html = renderToStaticMarkup(<StageCaption investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).toContain("Air temperature");
    expect(html).toContain("Helsinki");
    expect(html).toContain("60.2°N, 24.9°E · 1981 to 2025, all months");
  });

  test("names a season by its months", () => {
    const winter: Investigation = {
      ...investigation(SIGNIFICANT_RISE),
      requested: { from: 1991, to: 2020, season: "DJF" },
    };
    const html = renderToStaticMarkup(<StageCaption investigation={winter} />);
    expect(html).toContain("1991 to 2020, December to February");
  });

  test("lists every place of a comparison beside its marker, without coordinates", () => {
    const athens = placeResult(SIGNIFICANT_RISE);
    athens.place = { ...athens.place, name: "Athens", lat: 37.98, lon: 23.73 };
    const pair: Investigation = {
      ...investigation(SIGNIFICANT_RISE),
      results: [athens, placeResult(SIGNIFICANT_RISE)],
    };
    const html = renderToStaticMarkup(<StageCaption investigation={pair} />);
    expect(html).toContain("Athens");
    expect(html).toContain("Helsinki");
    expect(html.match(/shape-swatch/g)).toHaveLength(2);
    expect(html).not.toContain("°N");
  });

  test("is hidden from screen readers, which read the same in the case file", () => {
    const html = renderToStaticMarkup(<StageCaption investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).toContain('aria-hidden="true"');
  });
});
