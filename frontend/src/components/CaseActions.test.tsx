import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { CaseActions } from "./CaseActions";

const REGION = { url: "/map?v=air_temp&box=55,20,65,30", placeName: "Helsinki", onOpenPage: () => undefined };

describe("CaseActions", () => {
  test("offers to copy the link, and says nothing before it is pressed", () => {
    const html = renderToStaticMarkup(<CaseActions subject="case" />);
    expect(html).toContain("Copy link");
    expect(html).not.toContain("Link copied");
  });

  test("links a case to the map of the region around its place, and says what the map tests", () => {
    const html = renderToStaticMarkup(<CaseActions subject="case" region={REGION} />);
    expect(html).toContain('href="/map?v=air_temp&amp;box=55,20,65,30"');
    expect(html).toContain("Map this region");
    expect(html).toContain("shows the rate of change in every grid cell");
    expect(html).toContain("Significance is not assessed for the map.");
    expect(html).not.toContain("runs the same test");
  });

  test("offers no region link where there is none, as on a map", () => {
    expect(renderToStaticMarkup(<CaseActions subject="map" />)).not.toContain("Map this region");
  });
});
