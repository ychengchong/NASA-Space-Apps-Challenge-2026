import { describe, expect, test } from "vitest";
import { GLOBE_STYLE, LAYER, SEA_IMAGE, SOURCE } from "./globeStyle";

const layerIds = GLOBE_STYLE.layers.map((layer) => layer.id);

/** The parts of a layer the tests read. */
interface StyleLayer {
  minzoom?: number;
  filter?: unknown;
  layout?: unknown;
  paint?: unknown;
}

function layer(id: string): StyleLayer {
  const found = GLOBE_STYLE.layers.find((candidate) => candidate.id === id);
  if (found === undefined) throw new Error(`The style has no layer "${id}".`);
  return found;
}

describe("GLOBE_STYLE", () => {
  test("draws a globe", () => {
    expect(GLOBE_STYLE.projection).toEqual({ type: "globe" });
  });

  test("defines every source its layers read", () => {
    for (const layer of GLOBE_STYLE.layers) {
      if ("source" in layer) expect(Object.keys(GLOBE_STYLE.sources)).toContain(layer.source);
    }
  });

  test("starts every source the app fills in as an empty collection", () => {
    for (const source of Object.values(SOURCE)) {
      expect(GLOBE_STYLE.sources[source]).toEqual({
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
    }
  });

  test("holds every layer the globe looks cells up in, under a name of its own", () => {
    for (const layer of Object.values(LAYER)) expect(layerIds).toContain(layer);
    expect(new Set(layerIds).size).toBe(layerIds.length);
  });

  test("draws borders and names above the cells of a region map", () => {
    const cells = layerIds.indexOf(LAYER.cellFill);
    expect(layerIds.indexOf("country-border")).toBeGreaterThan(cells);
    expect(layerIds.indexOf("large-country-label")).toBeGreaterThan(cells);
  });

  test("draws the cells of a region map opaque, so a rate has the colour of the key", () => {
    expect(layer(LAYER.cellFill).paint).not.toHaveProperty("fill-opacity");
    expect(layer(LAYER.cellHatch).paint).not.toHaveProperty("fill-opacity");
  });

  test("draws the coast over the cells from the region view on", () => {
    expect(layerIds.indexOf("coast")).toBeGreaterThan(layerIds.indexOf(LAYER.cellHatch));
    expect(layer("coast")).toMatchObject({ type: "line", "source-layer": "water", minzoom: 3 });
  });

  test("names the oceans and the seas from the region view on, each in its own size", () => {
    expect(layer("ocean-label").minzoom).toBe(3);
    expect(JSON.stringify(layer("ocean-label").filter)).toContain('["in","Ocean"');
    expect(layer("sea-label").minzoom).toBe(3);
    expect(JSON.stringify(layer("sea-label").filter)).toContain('["!",["in","Ocean"');
  });

  test("names the best known countries from the whole-Earth view on, the rest closer in", () => {
    expect(layer("large-country-label").minzoom).toBe(0);
    expect(JSON.stringify(layer("large-country-label").filter)).toContain('["==",["get","rank"],1]');
    expect(layer("country-label").minzoom).toBe(3);
    expect(JSON.stringify(layer("country-label").filter)).toContain('["==",["get","rank"],2]');
    expect(layer("small-country-label").minzoom).toBe(3);
    expect(JSON.stringify(layer("small-country-label").filter)).toContain('[">",["get","rank"],2]');
  });

  test("engraves the graticule and the sea's lines under the cells of a region map", () => {
    const cells = layerIds.indexOf(LAYER.cellFill);
    expect(layerIds).toContain("graticule");
    expect(layerIds.indexOf("graticule")).toBeLessThan(cells);
    expect(layerIds.indexOf("water-lines")).toBeLessThan(cells);
    expect(JSON.stringify(GLOBE_STYLE.layers.find((candidate) => candidate.id === "water-lines"))).toContain(
      `"fill-pattern":"${SEA_IMAGE}"`,
    );
  });

  test("draws the sea in plain paper under its lines, for the moment before their image is ready", () => {
    expect(layerIds.indexOf("water")).toBeLessThan(layerIds.indexOf("water-lines"));
    expect(JSON.stringify(GLOBE_STYLE.layers.find((candidate) => candidate.id === "water"))).toContain(
      '"fill-color"',
    );
  });

  test("draws no glow of atmosphere round the Earth", () => {
    expect(GLOBE_STYLE.sky).toEqual({ "atmosphere-blend": 0 });
  });

  test("lets the best known countries keep their names where two would overlap", () => {
    expect(layerIds.indexOf("large-country-label")).toBeGreaterThan(layerIds.indexOf("country-label"));
    expect(layerIds.indexOf("country-label")).toBeGreaterThan(layerIds.indexOf("small-country-label"));
  });

  test("prints the longest country names in their short forms", () => {
    const name = JSON.stringify(layer("country-label").layout);
    expect(name).toContain('"Democratic Republic of the Congo","DR Congo"');
    expect(name).toContain('"Central African Republic","Central African Rep."');
  });

  test("takes its tiles and fonts from OpenFreeMap alone", () => {
    const urls = JSON.stringify(GLOBE_STYLE).match(/https?:\/\/[^/"]+/g) ?? [];
    expect(new Set(urls)).toEqual(new Set(["https://tiles.openfreemap.org"]));
  });
});
