import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test, vi } from "vitest";
import PlaceMap from "./PlaceMap";

// Leaflet needs a browser. The map itself is drawn in effects, which a static render never runs.
vi.mock("leaflet", () => ({}));
vi.mock("../leafletBase", () => ({ createBaseMap: () => undefined }));

describe("PlaceMap", () => {
  test("describes the outline of a 1 degree cell of sunlight and cloud like any other cell", () => {
    const html = renderToStaticMarkup(
      <PlaceMap
        places={[
          { name: "Helsinki", lat: 60.17, lon: 24.94, cell: { lat: 60.5, lon: 24.5, height: 1, width: 1 } },
        ]}
        onPick={() => undefined}
      />,
    );
    expect(html).toContain(
      "Helsinki: grid cell centred on 60.5°N, 24.5°E, 1° by 1°. The outline shows the cell the values describe.",
    );
  });
});
