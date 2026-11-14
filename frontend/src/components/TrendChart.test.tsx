import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { investigation, SIGNIFICANT_RISE } from "./testData";
import { TrendChart } from "./TrendChart";

function render(verdict = SIGNIFICANT_RISE): string {
  return renderToStaticMarkup(<TrendChart investigation={investigation(verdict)} />);
}

describe("TrendChart", () => {
  test("says in words how sure the rate of the trend line is, in the evidence panel's numbers", () => {
    expect(render()).toContain(
      "Its rate is +0.05 °C per decade; the 95% confidence interval of the rate runs from +0.03 to +0.07 °C per decade.",
    );
  });

  test("explains what a point is after the chart, so the chart follows its heading", () => {
    const html = render();
    const chart = html.indexOf("Loading the chart…");
    expect(chart).toBeGreaterThan(html.indexOf('id="chart-heading"'));
    expect(html.indexOf("Each point is")).toBeGreaterThan(chart);
  });

  test("is a sheet of the case file with a heading of its own and no exhibit label", () => {
    const html = render();
    expect(html).toContain('<section class="panel sheet" aria-labelledby="chart-heading">');
    expect(html).not.toContain("Exhibit");
  });
});
