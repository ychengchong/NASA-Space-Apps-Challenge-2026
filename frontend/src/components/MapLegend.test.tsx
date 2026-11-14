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

  test("explains the dot, the hatch and the stricter test", () => {
    const html = renderToStaticMarkup(<MapLegend variable={AIR_TEMP} limit={0.5} />);
    expect(html).toContain("Dot: the cell passes the map");
    expect(html).toContain("Hatched: no result");
    expect(html).toContain(
      "Marked cells pass a stricter test, because a map tests hundreds of cells at once.",
    );
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

  test("names the two marks in a few words", () => {
    const html = renderToStaticMarkup(<StageLegend trendMap={TREND_MAP} limit={0.5} />);
    expect(html).toContain("Passes the stricter test");
    expect(html).toContain("No result");
  });

  test("is hidden from screen readers, which read the full legend in its panel", () => {
    const html = renderToStaticMarkup(<StageLegend trendMap={TREND_MAP} limit={0.5} />);
    expect(html).toContain('aria-hidden="true"');
  });
});
