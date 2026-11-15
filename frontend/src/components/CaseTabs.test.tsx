import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { CaseTabs } from "./CaseTabs";

const PANELS = {
  answer: <p>The chart</p>,
  explore: <p>Explore further</p>,
  evidence: <p>The evidence panel</p>,
  learn: <p>The evidence lesson</p>,
};

describe("CaseTabs", () => {
  test("shows a row of four tabs with the answer chosen and one Tab stop", () => {
    const html = renderToStaticMarkup(<CaseTabs panels={PANELS} />);
    expect(html).toContain('role="tablist" aria-label="Case file"');
    expect(html.match(/role="tab"/g)).toHaveLength(4);
    expect(html).toContain(
      'role="tab" id="case-tab-answer" class="case-tab" aria-selected="true" aria-controls="case-panel-answer" tabindex="0"',
    );
    expect(html.match(/tabindex="-1"/g)).toHaveLength(3);
  });

  test("keeps every panel in the page, with all but the answer hidden", () => {
    const html = renderToStaticMarkup(<CaseTabs panels={PANELS} />);
    for (const text of ["The chart", "Explore further", "The evidence panel", "The evidence lesson"]) {
      expect(html).toContain(text);
    }
    expect(html).toContain('id="case-panel-answer" aria-labelledby="case-tab-answer"><p>The chart</p>');
    expect(html.match(/role="tabpanel"[^>]* hidden=""/g)).toHaveLength(3);
  });

  test("holds the panels in the order of the tabs", () => {
    const html = renderToStaticMarkup(<CaseTabs panels={PANELS} />);
    const order = ["The chart", "Explore further", "The evidence panel", "The evidence lesson"].map((text) =>
      html.indexOf(text),
    );
    expect(order).toEqual([...order].sort((a, b) => a - b));
  });
});
