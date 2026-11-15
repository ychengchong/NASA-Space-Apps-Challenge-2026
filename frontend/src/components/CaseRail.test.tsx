import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { CaseRail } from "./CaseRail";

describe("CaseRail", () => {
  test("keeps its children in place where the page has no right-hand column", () => {
    expect(
      renderToStaticMarkup(
        <div>
          <CaseRail>
            <p>Ask about this investigation</p>
          </CaseRail>
        </div>,
      ),
    ).toBe("<div><p>Ask about this investigation</p></div>");
  });
});
