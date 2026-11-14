import { describe, expect, test } from "vitest";
import type { CaseParams } from "./caseUrl";
import {
  casePageUrl,
  examplePageUrl,
  parseRoute,
  placePageUrl,
  sameCase,
  withRequestedPeriod,
  worldPageUrl,
} from "./route";

const HELSINKI_CASE: CaseParams = {
  variable: "air_temp",
  places: [{ lat: 60.17, lon: 24.94, name: "Helsinki" }],
  from: 1981,
  to: 2025,
  season: "annual",
};
const HELSINKI_SEARCH = "?v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual";

describe("parseRoute", () => {
  test("shows the first screen at the root", () => {
    expect(parseRoute("/", "")).toEqual({ kind: "home" });
  });

  test("shows the first screen for an unknown path", () => {
    expect(parseRoute("/about", "")).toEqual({ kind: "home" });
  });

  test("opens the case named by a case page's address", () => {
    expect(parseRoute("/case", HELSINKI_SEARCH)).toEqual({ kind: "case", params: HELSINKI_CASE });
  });

  test("accepts a trailing slash after the case path", () => {
    expect(parseRoute("/case/", HELSINKI_SEARCH)).toEqual({ kind: "case", params: HELSINKI_CASE });
  });

  test("drops the scan, which is not part of the case", () => {
    expect(parseRoute("/case", `${HELSINKI_SEARCH}&scan=1`)).toEqual({ kind: "case", params: HELSINKI_CASE });
  });

  test("explains a case link it cannot read", () => {
    expect(parseRoute("/case", "?p=60.17,24.94")).toEqual({
      kind: "bad_link",
      reason: "The link does not name a variable.",
    });
  });

  test("keeps the map's parameters for the region view", () => {
    expect(parseRoute("/map", "?v=air_temp&box=55,20,65,30")).toEqual({
      kind: "map",
      query: "v=air_temp&box=55,20,65,30",
    });
  });
});

describe("casePageUrl", () => {
  test("writes the full case, period and season included", () => {
    expect(casePageUrl(HELSINKI_CASE)).toBe(`/case${HELSINKI_SEARCH}`);
  });

  test("never writes the scan into the address", () => {
    expect(casePageUrl({ ...HELSINKI_CASE, scan: true })).toBe(`/case${HELSINKI_SEARCH}`);
  });

  test("reopens the same case from its own address", () => {
    const url = new URL(casePageUrl(HELSINKI_CASE), "https://example.org");
    expect(parseRoute(url.pathname, url.search)).toEqual({ kind: "case", params: HELSINKI_CASE });
  });
});

describe("examplePageUrl", () => {
  test("opens an example's parameter string as a case page", () => {
    expect(examplePageUrl("v=air_temp&p=60.17,24.94")).toBe("/case?v=air_temp&p=60.17,24.94");
  });
});

describe("withRequestedPeriod", () => {
  test("fills in the period the API used when the link gave none", () => {
    const params: CaseParams = {
      variable: "air_temp",
      places: [{ lat: 60.17, lon: 24.94 }],
      season: "annual",
    };
    expect(withRequestedPeriod(params, { from: 1981, to: 2025, season: "annual" })).toEqual({
      ...params,
      from: 1981,
      to: 2025,
    });
  });

  test("replaces years outside the record with the clamped years", () => {
    const clamped = withRequestedPeriod(
      { ...HELSINKI_CASE, from: 1950, to: 2040 },
      { from: 1981, to: 2025, season: "annual" },
    );
    expect(sameCase(clamped, HELSINKI_CASE)).toBe(true);
  });
});

describe("sameCase", () => {
  test("ignores the scan option", () => {
    expect(sameCase({ ...HELSINKI_CASE, scan: true }, HELSINKI_CASE)).toBe(true);
  });

  test("tells apart cases with different periods", () => {
    expect(sameCase({ ...HELSINKI_CASE, from: 1990 }, HELSINKI_CASE)).toBe(false);
  });
});

describe("place overview routes", () => {
  test("reads /place as a place's overview and builds the same address back", () => {
    const route = parseRoute("/place", "?p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual");
    expect(route.kind).toBe("place");
    if (route.kind !== "place") return;
    expect(route.params.place).toEqual({ lat: 60.17, lon: 24.94, name: "Helsinki" });
    expect(placePageUrl(route.params)).toBe("/place?p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual");
  });

  test("calls an overview of two places a link the app cannot read", () => {
    expect(parseRoute("/place", "?p=60.17,24.94&p=1,2").kind).toBe("bad_link");
  });
});

describe("whole world routes", () => {
  test("reads /world as a variable's world trend and builds the same address back", () => {
    const route = parseRoute("/world", "?v=air_temp&from=1981&to=2025&s=annual");
    expect(route.kind).toBe("world");
    if (route.kind !== "world") return;
    expect(worldPageUrl(route.params)).toBe("/world?v=air_temp&from=1981&to=2025&s=annual");
  });

  test("calls a world link without a variable a link the app cannot read", () => {
    expect(parseRoute("/world", "?from=1981").kind).toBe("bad_link");
  });
});
