import { describe, expect, test } from "vitest";
import { citationHref, citationLabel } from "./citations";
import { CITATION, PROJECT_CITATION } from "./components/testData";

describe("citationLabel", () => {
  test("names the publisher, the title and the section without repeating the title", () => {
    expect(citationLabel(CITATION)).toBe(
      "NASA Langley Research Center, POWER Project · POWER Meteorological Data Sources · MERRA-2",
    );
  });

  test("leaves out a section that only repeats the title", () => {
    expect(citationLabel(PROJECT_CITATION)).toBe(
      "Trend Detective project · Sen's slope and the total change",
    );
  });

  test("keeps a section that is not named after the title", () => {
    expect(citationLabel({ ...CITATION, section: "Data access" })).toBe(
      "NASA Langley Research Center, POWER Project · POWER Meteorological Data Sources · Data access",
    );
  });

  test("leaves out an empty section", () => {
    expect(citationLabel({ ...CITATION, section: "" })).toBe(
      "NASA Langley Research Center, POWER Project · POWER Meteorological Data Sources",
    );
  });
});

describe("citationHref", () => {
  test("links to the manifest's HTTPS address", () => {
    expect(citationHref(CITATION)).toBe(CITATION.url);
  });

  test.each(["javascript:alert(1)", "http://power.larc.nasa.gov/", "data:text/html,hi", "/docs/method"])(
    "gives no link for %s",
    (url) => {
      expect(citationHref({ ...CITATION, url })).toBeNull();
    },
  );
});
