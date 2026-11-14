import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { GLOBE_UNAVAILABLE, GlobeContext } from "../globeContext";
import type { MapPlace } from "../mapCell";
import { PlaceLegend } from "./PlaceLegend";

const HELSINKI: MapPlace = { name: "Helsinki", lat: 60.17, lon: 24.94 };
const HELSINKI_SUNLIGHT: MapPlace = { ...HELSINKI, cell: { lat: 60.5, lon: 24.5, height: 1, width: 1 } };

describe("PlaceLegend", () => {
  test("describes the outline of a 1 degree cell of sunlight and cloud like any other cell", () => {
    const html = renderToStaticMarkup(<PlaceLegend places={[HELSINKI_SUNLIGHT]} pickedPoint={null} />);
    expect(html).toContain(
      "Helsinki: grid cell centred on 60.5°N, 24.5°E, 1° by 1°. The outline shows the cell the values describe.",
    );
  });

  test("names a place by its point before its case has run", () => {
    const html = renderToStaticMarkup(<PlaceLegend places={[HELSINKI]} pickedPoint={null} />);
    expect(html).toContain("Helsinki: 60.2°N, 24.9°E");
    expect(html).not.toContain("Zoom in to the grid cell");
  });

  test("offers to zoom in once a place has a grid cell to show", () => {
    const html = renderToStaticMarkup(<PlaceLegend places={[HELSINKI_SUNLIGHT]} pickedPoint={null} />);
    expect(html).toContain("Zoom in to the grid cell");
  });

  test("says how to pick a point on the globe by mouse and by keyboard", () => {
    const html = renderToStaticMarkup(<PlaceLegend places={[]} pickedPoint={null} />);
    expect(html).toContain("Click the globe to pick a point");
    expect(html).toContain("press Enter to pick the point at its centre");
  });

  test("names the point picked on the globe and where its choices are", () => {
    const html = renderToStaticMarkup(<PlaceLegend places={[]} pickedPoint={{ lat: -1.29, lon: 36.82 }} />);
    expect(html).toContain("You picked 1.3°S, 36.8°E. Choose what to do with it on the globe.");
  });

  test("points to the place search when the browser cannot draw the globe", () => {
    const html = renderToStaticMarkup(
      <GlobeContext value={GLOBE_UNAVAILABLE}>
        <PlaceLegend places={[]} pickedPoint={null} />
      </GlobeContext>,
    );
    expect(html).toContain("The globe could not start in this browser");
    expect(html).not.toContain("Click the globe to pick a point");
  });
});
