import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { MapLegend, StageLegend } from "./MapLegend";
import { AIR_TEMP, TREND_MAP } from "./testData";

describe("MapLegend", () => {
  test("gives the scale its units and its two ends", () => {
    const html = renderToStaticMarkup(<MapLegend variable={AIR_TEMP} limit={0.5} />);
    expect(html).toContain("Rate of change, °C per decade");
    expect(html).toContain("-0.50");
    expect(html).toContain("+0.50");
  });

  test("explains the hatch and says the map's rates are descriptive", () => {
    const html = renderToStaticMarkup(<MapLegend variable={AIR_TEMP} limit={0.5} />);
    expect(html).toContain("Hatched: no rate is available");
    expect(html).toContain("Regional maps show descriptive rates. Significance is not assessed.");
    expect(html).not.toContain("stricter test");
  });
});

describe("StageLegend", () => {
  test("names the variable, the scale with its ends, and the period", () => {
    const html = renderToStaticMarkup(<StageLegend trendMap={TREND_MAP} limit={0.5} />);
    expect(html).toContain("Air temperature");
    expect(html).toContain("Rate of change, °C per decade");
    expect(html).toContain("-0.50");
    expect(html).toContain("+0.50");
    expect(html).toContain("1981 to 2025, all months");
  });

  test("names the hatch in a few words", () => {
    const html = renderToStaticMarkup(<StageLegend trendMap={TREND_MAP} limit={0.5} />);
    expect(html).toContain("No rate");
    expect(html).not.toContain("stricter test");
  });

  test("is hidden from screen readers, which read the full legend in its panel", () => {
    const html = renderToStaticMarkup(<StageLegend trendMap={TREND_MAP} limit={0.5} />);
    expect(html).toContain('aria-hidden="true"');
  });
});
