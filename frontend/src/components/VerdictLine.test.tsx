import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { investigation, placeResult, SIGNIFICANT_RISE } from "./testData";
import { VerdictLine } from "./VerdictLine";

describe("VerdictLine", () => {
  test("repeats the card's figure and stamp words, hidden from screen readers", () => {
    const html = renderToStaticMarkup(<VerdictLine investigation={investigation(SIGNIFICANT_RISE)} shown />);
    expect(html).toContain('<p class="verdict-line is-shown" aria-hidden="true">');
    expect(html).toContain('<span class="verdict-line-figure">+0.05 °C per decade</span>');
    expect(html).toContain("↑ Rising · Significant");
  });

  test("holds nothing that takes keyboard focus", () => {
    const html = renderToStaticMarkup(<VerdictLine investigation={investigation(SIGNIFICANT_RISE)} shown />);
    expect(html).not.toMatch(/<(a|button|input|summary)\b|tabindex/);
  });

  test("stays in the page but out of sight until the card has scrolled away", () => {
    const html = renderToStaticMarkup(
      <VerdictLine investigation={investigation(SIGNIFICANT_RISE)} shown={false} />,
    );
    expect(html).toContain('<p class="verdict-line" aria-hidden="true">');
  });

  test("marks each place of a comparison with its shape", () => {
    const athens = placeResult(SIGNIFICANT_RISE);
    athens.place = { ...athens.place, name: "Athens" };
    const both = { ...investigation(SIGNIFICANT_RISE), results: [athens, placeResult(SIGNIFICANT_RISE)] };
    const html = renderToStaticMarkup(<VerdictLine investigation={both} shown />);
    expect(html.match(/shape-swatch/g)).toHaveLength(2);
    expect(html).toContain('<span class="verdict-line-name">Athens</span>');
    expect(html).toContain('<span class="verdict-line-name">Helsinki</span>');
  });
});
