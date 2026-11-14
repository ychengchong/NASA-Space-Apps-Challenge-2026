import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { FileTab } from "./FileTab";

describe("FileTab", () => {
  test("names the sheet", () => {
    expect(renderToStaticMarkup(<FileTab label="Case file" />)).toBe('<p class="file-tab">Case file</p>');
  });
});
