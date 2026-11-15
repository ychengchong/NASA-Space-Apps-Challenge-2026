import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { EvidencePanel } from "./EvidencePanel";
import { investigation, placeResult, SIGNIFICANT_RISE } from "./testData";

describe("EvidencePanel", () => {
  test("names a 1 degree cell of sunlight and cloud by its centre and size", () => {
    const result = placeResult(SIGNIFICANT_RISE);
    const oneDegree = {
      ...result,
      place: { ...result.place, cell: { lat: 60.5, lon: 24.5, height: 1, width: 1 } },
    };
    const html = renderToStaticMarkup(
      <EvidencePanel investigation={{ ...investigation(SIGNIFICANT_RISE), results: [oneDegree] }} />,
    );
    expect(html).toContain("centred on 60.5°N, 24.5°E, 1° by 1°");
  });

  test("is open in its tab, so the numbers are one click from the answer", () => {
    const html = renderToStaticMarkup(<EvidencePanel investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).not.toContain("<details");
    expect(html).toContain("<h3>Numbers</h3>");
  });
});
