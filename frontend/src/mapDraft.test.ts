import { describe, expect, test } from "vitest";
import { boxText, draftFromMapQuery, EMPTY_MAP_DRAFT, mapFromDraft } from "./mapDraft";
import type { MapDraft } from "./mapDraft";

const FINLAND: MapDraft = {
  variable: "air_temp",
  fromText: "1981",
  toText: "2025",
  season: "JJA",
  box: { south: "55", west: "20", north: "65", east: "30" },
};

describe("draftFromMapQuery", () => {
  test("fills the settings from a map's query string", () => {
    expect(draftFromMapQuery("v=air_temp&from=1981&to=2025&s=JJA&box=55,20,65,30")).toEqual(FINLAND);
  });

  test("leaves the years empty when the link gives none", () => {
    expect(draftFromMapQuery("v=air_temp&box=55,20,65,30")).toMatchObject({ fromText: "", toText: "" });
  });

  test("starts empty for a query that is not a map", () => {
    expect(draftFromMapQuery("")).toEqual(EMPTY_MAP_DRAFT);
  });
});

describe("mapFromDraft", () => {
  test("turns a complete draft into a map", () => {
    expect(mapFromDraft(FINLAND)).toEqual({
      ok: true,
      value: {
        variable: "air_temp",
        from: 1981,
        to: 2025,
        season: "JJA",
        box: { south: 55, west: 20, north: 65, east: 30 },
      },
    });
  });

  test("leaves out empty years, which mean the whole record", () => {
    const result = mapFromDraft({ ...FINLAND, fromText: "", toText: " " });
    expect(result.ok && result.value.from === undefined && result.value.to === undefined).toBe(true);
  });

  test("asks for a variable first", () => {
    expect(mapFromDraft({ ...FINLAND, variable: null })).toEqual({ ok: false, reason: "Choose a variable." });
  });

  test("refuses a year that is not four digits", () => {
    expect(mapFromDraft({ ...FINLAND, fromText: "81" }).ok).toBe(false);
  });

  test("refuses a first year after the last", () => {
    expect(mapFromDraft({ ...FINLAND, fromText: "2020", toText: "2000" })).toEqual({
      ok: false,
      reason: "The first year must not be later than the last year.",
    });
  });

  test("refuses an edge that is empty or not a number", () => {
    expect(mapFromDraft({ ...FINLAND, box: { ...FINLAND.box, east: "" } }).ok).toBe(false);
    expect(mapFromDraft({ ...FINLAND, box: { ...FINLAND.box, north: "65N" } }).ok).toBe(false);
  });

  test("refuses a box outside the globe", () => {
    expect(mapFromDraft({ ...FINLAND, box: { ...FINLAND.box, north: "95" } })).toEqual({
      ok: false,
      reason: "The box reaches outside the globe.",
    });
  });

  test("leaves the size of the box to the API", () => {
    expect(mapFromDraft({ ...FINLAND, box: { south: "0", west: "0", north: "40", east: "40" } }).ok).toBe(
      true,
    );
  });
});

describe("boxText", () => {
  test("writes each edge as typed numbers", () => {
    expect(boxText({ south: -12.5, west: 20, north: -2.5, east: 30 })).toEqual({
      south: "-12.5",
      west: "20",
      north: "-2.5",
      east: "30",
    });
  });
});
