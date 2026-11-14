import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { CaseLayout } from "./CaseLayout";

describe("CaseLayout", () => {
  test("holds the answer first, then the settings, then the evidence, the order on screen", () => {
    const html = renderToStaticMarkup(
      <CaseLayout side={<p>Settings</p>} answer={<p>Verdict</p>} main={<p>Chart</p>} />,
    );
    const verdict = html.indexOf("Verdict");
    const settings = html.indexOf("Settings");
    const chart = html.indexOf("Chart");
    expect(verdict).toBeGreaterThanOrEqual(0);
    expect(verdict).toBeLessThan(settings);
    expect(settings).toBeLessThan(chart);
  });
});
