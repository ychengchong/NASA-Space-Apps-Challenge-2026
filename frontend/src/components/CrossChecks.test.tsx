import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { VariableSummary } from "../api";
import type { CaseParams } from "../caseUrl";
import { pickedRegionTypes } from "../regionTypes";
import type { RegionTypes } from "../regionTypes";
import { CrossChecks } from "./CrossChecks";
import { AIR_TEMP } from "./testData";

const AIR_TEMP_WITH_RELATED: VariableSummary = {
  ...AIR_TEMP,
  related: ["surface_temp"],
  region_types: ["tundra"],
};
const SURFACE_TEMP: VariableSummary = {
  ...AIR_TEMP,
  id: "surface_temp",
  name: "Surface (skin) temperature",
  related: ["air_temp"],
  region_types: ["tundra", "desert"],
};
const PRECIPITATION: VariableSummary = {
  ...AIR_TEMP,
  id: "precipitation",
  name: "Precipitation",
  related: [],
  region_types: ["desert"],
};
const CATALOGUE = [AIR_TEMP_WITH_RELATED, SURFACE_TEMP, PRECIPITATION];

const SAHARA_CASE: CaseParams = {
  variable: "air_temp",
  places: [{ lat: 23, lon: 12, name: "Sahara" }],
  from: 1990,
  to: 2020,
  season: "JJA",
};
const SAHARA_IS_DESERT: RegionTypes = new Map(
  pickedRegionTypes([{ name: "Sahara", lat: 23, lon: 12, kind: "region", region_type: "desert" }]),
);

function renderCrossChecks(params: CaseParams, regionTypes: RegionTypes): string {
  return renderToStaticMarkup(
    <CrossChecks
      params={params}
      variables={CATALOGUE}
      regionTypes={regionTypes}
      onOpenPage={() => undefined}
    />,
  );
}

describe("CrossChecks", () => {
  test("links each related variable with the same places, period and season", () => {
    const html = renderCrossChecks(SAHARA_CASE, new Map());
    expect(html).toContain("Cross-check with a related variable");
    expect(html).toContain(
      'href="/case?v=surface_temp&amp;p=23,12&amp;label=Sahara&amp;from=1990&amp;to=2020&amp;s=JJA"',
    );
    expect(html).toContain("Surface (skin) temperature</a>");
  });

  test("links the variables worth testing in the place's region type", () => {
    const html = renderCrossChecks(SAHARA_CASE, SAHARA_IS_DESERT);
    expect(html).toContain("Worth testing here");
    expect(html).toContain("Sahara · desert");
    expect(html).toContain(
      'href="/case?v=precipitation&amp;p=23,12&amp;label=Sahara&amp;from=1990&amp;to=2020&amp;s=JJA"',
    );
  });

  test("shows no region-type suggestions when the place's region type is not known", () => {
    const html = renderCrossChecks(SAHARA_CASE, new Map());
    expect(html).not.toContain("Worth testing here");
    expect(html).not.toContain("v=precipitation");
  });

  test("shows a place label as plain text", () => {
    const label = "<b>Sahara</b>";
    const params = { ...SAHARA_CASE, places: [{ lat: 23, lon: 12, name: label }] };
    const regionTypes: RegionTypes = new Map(
      pickedRegionTypes([{ name: label, lat: 23, lon: 12, kind: "region", region_type: "desert" }]),
    );
    const html = renderCrossChecks(params, regionTypes);
    expect(html).toContain("&lt;b&gt;Sahara&lt;/b&gt; · desert");
    expect(html).not.toContain("<b>");
  });

  test("shows nothing for a variable with no related variable and no known region type", () => {
    expect(renderCrossChecks({ ...SAHARA_CASE, variable: "precipitation" }, new Map())).toBe("");
  });
});
