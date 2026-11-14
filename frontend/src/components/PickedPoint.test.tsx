import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { CasePlace } from "../caseUrl";
import { PickedPoint } from "./PickedPoint";

const POINT: CasePlace = { lat: -1.29, lon: 36.82 };
const HELSINKI: CasePlace = { lat: 60.17, lon: 24.94, name: "Helsinki" };

function renderPoint(places: readonly CasePlace[]): string {
  return renderToStaticMarkup(
    <PickedPoint
      point={POINT}
      places={places}
      onChoose={() => undefined}
      onDismiss={() => undefined}
      overviewUrl="/place?p=-1.29,36.82&s=annual"
      onOpenPage={() => undefined}
    />,
  );
}

describe("PickedPoint", () => {
  test("names the point by its coordinates", () => {
    expect(renderPoint([])).toContain("You picked 1.3°S, 36.8°E");
  });

  test("offers to use the point when the case has no place yet", () => {
    const html = renderPoint([]);
    expect(html).toContain("Use this place");
    expect(html).not.toContain("Compare with");
  });

  test("offers to replace the place of a case or to compare with it, in short labels", () => {
    const html = renderPoint([HELSINKI]);
    expect(html).toContain('<span aria-hidden="true">Use instead</span>');
    expect(html).toContain('<span aria-hidden="true">Compare</span>');
  });

  test("reads the full labels out to screen readers", () => {
    const html = renderPoint([HELSINKI]);
    expect(html).toContain('<span class="visually-hidden">Use instead of Helsinki</span>');
    expect(html).toContain('<span class="visually-hidden">Compare with Helsinki</span>');
  });

  test("can always be dismissed", () => {
    expect(renderPoint([HELSINKI])).toContain("Dismiss");
  });

  test("offers what is changing at the point, as a link to its overview", () => {
    const html = renderPoint([]);
    expect(html).toContain('href="/place?p=-1.29,36.82&amp;s=annual"');
    expect(html).toContain("What is changing here?");
  });
});
