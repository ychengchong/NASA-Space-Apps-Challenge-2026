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

  test("gathers the ways on from a case under Explore further, each with one line", () => {
    const overview = { url: "/place?p=60.17,24.94", placeName: "Helsinki", onOpenPage: () => undefined };
    const world = { url: "/world?v=air_temp", placeName: "the whole world", onOpenPage: () => undefined };
    const html = renderToStaticMarkup(
      <CaseActions subject="case" region={REGION} overview={overview} world={world} />,
    );
    expect(html).toContain("Explore further");
    const titles = ["What is changing here?", "The whole world", "Map this region"];
    const positions = titles.map((title) => html.indexOf(title));
    expect(positions.every((position) => position >= 0)).toBe(true);
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);
    expect(html).toContain("The rate of every variable at Helsinki.");
  });

  test("does not repeat the folded panels of the case's own page among the ways on", () => {
    const html = renderToStaticMarkup(<CaseActions subject="case" region={REGION} />);
    expect(html).not.toContain("Compare the seasons");
    expect(html).not.toContain("Explore the period");
  });

  test("sets the other variables to test inside the Explore further sheet, after its links", () => {
    const html = renderToStaticMarkup(
      <CaseActions subject="case" region={REGION} more={<p>Test another variable</p>} />,
    );
    const sheet = html.slice(html.indexOf("<nav"), html.indexOf("</nav>"));
    expect(sheet.indexOf("Test another variable")).toBeGreaterThan(sheet.indexOf("Map this region"));
  });

  test("shows no Explore further group on a map, which has none of these ways", () => {
    expect(renderToStaticMarkup(<CaseActions subject="map" />)).not.toContain("Explore further");
  });
});
