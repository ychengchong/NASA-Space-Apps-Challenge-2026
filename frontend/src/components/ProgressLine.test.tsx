import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { ProgressLine } from "./ProgressLine";

describe("ProgressLine", () => {
  test("first enters the page empty, so screen readers announce the label when it appears", () => {
    const html = renderToStaticMarkup(<ProgressLine active label="Getting the data…" />);
    expect(html).toContain('role="status"');
    expect(html).not.toContain("Getting the data…");
  });
});
