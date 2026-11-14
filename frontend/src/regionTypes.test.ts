import { describe, expect, test } from "vitest";
import type { PlaceCandidate } from "./api";
import { parseCaseQuery } from "./caseUrl";
import type { CasePlace } from "./caseUrl";
import {
  lookUpRegionType,
  pickedRegionTypes,
  placeKey,
  placesToLookUp,
  regionTypeFromLookup,
  regionTypeOf,
} from "./regionTypes";
import type { NamedPlace } from "./regionTypes";

const SAHARA: PlaceCandidate = { name: "Sahara", lat: 23, lon: 12, kind: "region", region_type: "desert" };
const SHANGHAI: PlaceCandidate = {
  name: "Shanghai",
  country: "China",
  lat: 31.2222,
  lon: 121.4581,
  kind: "city",
  region_type: "megacity",
};
const SVALBARD: PlaceCandidate = {
  name: "Svalbard",
  country: "Norway",
  lat: 78.22,
  lon: 15.65,
  kind: "region",
  region_type: "tundra",
};
const HELSINKI: PlaceCandidate = {
  name: "Helsinki",
  country: "Finland",
  lat: 60.1695,
  lon: 24.9354,
  kind: "city",
};

const NOTHING_KNOWN = new Map<string, string | null>();
const NOTHING_ASKED = new Set<string>();

/** The first place of a case opened from a link with this query string. */
function linkedPlace(query: string): CasePlace {
  const parsed = parseCaseQuery(query);
  if (!parsed.ok) throw new Error(parsed.reason);
  const [place] = parsed.value.places;
  if (place === undefined) throw new Error("The link has no place.");
  return place;
}

describe("pickedRegionTypes", () => {
  test("keeps the region type of a place picked from the list for the case it opens", () => {
    const known = new Map(pickedRegionTypes([SAHARA]));
    expect(regionTypeOf(known, linkedPlace("v=air_temp&p=23,12&label=Sahara"))).toBe("desert");
  });

  test("keeps the region type of a city tagged as a megacity", () => {
    const known = new Map(pickedRegionTypes([SHANGHAI]));
    expect(regionTypeOf(known, linkedPlace("v=air_temp&p=31.2222,121.4581&label=Shanghai"))).toBe("megacity");
  });

  test("records a picked place without a region type as having none", () => {
    expect(pickedRegionTypes([HELSINKI])).toEqual([["60.1695,24.9354 Helsinki", null]]);
  });

  test("gives no region type to an unnamed place at the same point", () => {
    const known = new Map(pickedRegionTypes([SAHARA]));
    expect(regionTypeOf(known, linkedPlace("v=air_temp&p=23,12"))).toBeNull();
  });
});

describe("regionTypeFromLookup", () => {
  test("takes the region type of a region whose name and link coordinates match the place", () => {
    const place = linkedPlace("v=air_temp&p=23,12&label=Sahara");
    expect(regionTypeFromLookup(place, [SAHARA])).toBe("desert");
  });

  test("compares coordinates after rounding them as a link does", () => {
    const place = linkedPlace("v=air_temp&p=72.6,-38.5&label=Greenland ice sheet");
    const candidate: PlaceCandidate = {
      name: "Greenland ice sheet",
      lat: 72.601,
      lon: -38.499,
      kind: "region",
      region_type: "ice sheet",
    };
    expect(regionTypeFromLookup(place, [candidate])).toBeNull();
  });

  test("takes the megacity type of a city whose name and link coordinates match", () => {
    const place = linkedPlace("v=min_temp&p=31.2222,121.4581&label=Shanghai");
    expect(regionTypeFromLookup(place, [SHANGHAI])).toBe("megacity");
  });

  test("gives no region type for a matching city that has none", () => {
    const place = linkedPlace("v=air_temp&p=60.1695,24.9354&label=Helsinki");
    expect(regionTypeFromLookup(place, [HELSINKI])).toBeNull();
  });

  test("takes the region type of a region its alternative name found at the same point", () => {
    // The headline example labels the place Longyearbyen, an alternative name of Svalbard.
    const place = linkedPlace("v=air_temp&p=78.22,15.65&label=Longyearbyen");
    expect(regionTypeFromLookup(place, [SVALBARD])).toBe("tundra");
  });

  test("takes the region type of a region labelled by another of its names", () => {
    const place = linkedPlace("v=air_temp&p=23,12&label=Sahara Desert");
    expect(regionTypeFromLookup(place, [SAHARA])).toBe("desert");
  });

  test("ignores a region of the same name at another point", () => {
    const place = linkedPlace("v=air_temp&p=60.17,24.94&label=Sahara");
    expect(regionTypeFromLookup(place, [SAHARA])).toBeNull();
  });
});

describe("placesToLookUp", () => {
  test("looks up a named place once, even when the case holds it twice", () => {
    const sahara = linkedPlace("v=air_temp&p=23,12&label=Sahara");
    expect(placesToLookUp([sahara, sahara], NOTHING_KNOWN, NOTHING_ASKED)).toEqual([sahara]);
  });

  test("never looks up an unnamed place", () => {
    const point = linkedPlace("v=air_temp&p=23,12");
    expect(placesToLookUp([point], NOTHING_KNOWN, NOTHING_ASKED)).toEqual([]);
  });

  test("skips a place whose region type is known, even as none", () => {
    const helsinki = linkedPlace("v=air_temp&p=60.1695,24.9354&label=Helsinki");
    const known = new Map(pickedRegionTypes([HELSINKI]));
    expect(placesToLookUp([helsinki], known, NOTHING_ASKED)).toEqual([]);
  });

  test("skips a place already asked about while its answer is on the way", () => {
    const sahara = linkedPlace("v=air_temp&p=23,12&label=Sahara");
    expect(placesToLookUp([sahara], NOTHING_KNOWN, new Set([placeKey(sahara)]))).toEqual([]);
  });
});

describe("lookUpRegionType", () => {
  const LONGYEARBYEN: NamedPlace = { lat: 78.22, lon: 15.65, name: "Longyearbyen" };

  test("records the region type that a lookup of the place's label gives", async () => {
    const findPlaces = (label: string): Promise<PlaceCandidate[]> =>
      Promise.resolve(label === "Longyearbyen" ? [SVALBARD] : []);
    expect(await lookUpRegionType(LONGYEARBYEN, findPlaces)).toEqual([placeKey(LONGYEARBYEN), "tundra"]);
  });

  test("leaves the region type unknown when the lookup fails", async () => {
    const findPlaces = (): Promise<PlaceCandidate[]> => Promise.reject(new Error("The service is down."));
    expect(await lookUpRegionType(LONGYEARBYEN, findPlaces)).toBeNull();
  });
});
