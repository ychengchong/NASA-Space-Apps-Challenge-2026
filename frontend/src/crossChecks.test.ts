import { describe, expect, test } from "vitest";
import type { VariableSummary } from "./api";
import type { CaseParams, CasePlace } from "./caseUrl";
import { regionTypeSuggestions, relatedVariables, withVariable } from "./crossChecks";
import { casePageUrl } from "./route";

function variable(id: string, related: string[], region_types: string[]): VariableSummary {
  return {
    id,
    name: id,
    definition: "",
    units: "",
    rate_units: "",
    decimals: 2,
    theme: "test",
    record_start: 1981,
    related,
    region_types,
  };
}

const AIR_TEMP = variable("air_temp", ["surface_temp", "precipitation"], ["tundra", "mountains"]);
const SURFACE_TEMP = variable("surface_temp", ["air_temp"], ["tundra"]);
const PRECIPITATION = variable("precipitation", ["soil_wetness"], ["desert", "mountains"]);
const SOIL_WETNESS = variable("soil_wetness", [], ["desert"]);
const CATALOGUE = [AIR_TEMP, SURFACE_TEMP, PRECIPITATION, SOIL_WETNESS];

const SAHARA: CasePlace = { lat: 23, lon: 12, name: "Sahara" };
const GOBI: CasePlace = { lat: 43, lon: 105, name: "Gobi Desert" };
const ALPS: CasePlace = { lat: 46.5, lon: 8.5, name: "Alps" };
const HELSINKI: CasePlace = { lat: 60.17, lon: 24.94, name: "Helsinki" };

const REGION_TYPES: ReadonlyMap<string, string> = new Map([
  ["Sahara", "desert"],
  ["Gobi Desert", "desert"],
  ["Alps", "mountains"],
]);

function regionTypeOf(place: CasePlace): string | null {
  return REGION_TYPES.get(place.name ?? "") ?? null;
}

describe("withVariable", () => {
  test("switches the variable and keeps the places, period and season", () => {
    const params: CaseParams = {
      variable: "air_temp",
      places: [SAHARA, HELSINKI],
      from: 1990,
      to: 2020,
      season: "JJA",
    };
    expect(casePageUrl(withVariable(params, "precipitation"))).toBe(
      "/case?v=precipitation&p=23,12&p=60.17,24.94&label=Sahara&label=Helsinki&from=1990&to=2020&s=JJA",
    );
  });
});

describe("relatedVariables", () => {
  test("gives the related variables from the catalogue, in the order the variable lists them", () => {
    expect(relatedVariables(AIR_TEMP, CATALOGUE)).toEqual([SURFACE_TEMP, PRECIPITATION]);
  });

  test("leaves out a related id that is not in the catalogue", () => {
    const withUnknown = { ...AIR_TEMP, related: ["cloud", "precipitation"] };
    expect(relatedVariables(withUnknown, CATALOGUE)).toEqual([PRECIPITATION]);
  });
});

describe("regionTypeSuggestions", () => {
  test("suggests the variables worth testing in the place's region type, in catalogue order", () => {
    expect(regionTypeSuggestions([SAHARA], regionTypeOf, CATALOGUE, AIR_TEMP)).toEqual([
      { regionType: "desert", placeNames: ["Sahara"], variables: [PRECIPITATION, SOIL_WETNESS] },
    ]);
  });

  test("leaves out the case's own variable", () => {
    const [suggestion] = regionTypeSuggestions([SAHARA], regionTypeOf, CATALOGUE, PRECIPITATION);
    expect(suggestion?.variables).toEqual([SOIL_WETNESS]);
  });

  test("suggests nothing for a place whose region type is not known", () => {
    expect(regionTypeSuggestions([HELSINKI], regionTypeOf, CATALOGUE, AIR_TEMP)).toEqual([]);
  });

  test("names every place of a region type once, under one suggestion", () => {
    const suggestions = regionTypeSuggestions([SAHARA, ALPS, GOBI], regionTypeOf, CATALOGUE, AIR_TEMP);
    expect(suggestions.map((suggestion) => [suggestion.regionType, suggestion.placeNames])).toEqual([
      ["desert", ["Sahara", "Gobi Desert"]],
      ["mountains", ["Alps"]],
    ]);
  });

  test("suggests nothing for a region type whose only variable is the case's own", () => {
    const onlyAirTemp = [AIR_TEMP, variable("cloud", [], [])];
    expect(regionTypeSuggestions([ALPS], regionTypeOf, onlyAirTemp, AIR_TEMP)).toEqual([]);
  });
});
