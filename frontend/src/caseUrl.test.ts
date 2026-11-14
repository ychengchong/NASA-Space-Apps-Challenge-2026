import { describe, expect, test } from "vitest";
import { buildCaseQuery, buildMapQuery, buildSeriesQuery, parseCaseQuery, parseMapQuery } from "./caseUrl";
import type { CaseParams, MapParams, ParseResult } from "./caseUrl";

const HELSINKI_CASE: CaseParams = {
  variable: "air_temp",
  places: [{ lat: 60.17, lon: 24.94, name: "Helsinki" }],
  from: 1981,
  to: 2025,
  season: "annual",
};

const HELSINKI_QUERY = "v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual";

function reasonOf<T>(result: ParseResult<T>): string {
  if (result.ok) throw new Error("Expected the query to be invalid.");
  return result.reason;
}

describe("buildCaseQuery", () => {
  test("writes the example from spec section 10", () => {
    expect(buildCaseQuery(HELSINKI_CASE)).toBe(HELSINKI_QUERY);
  });

  test("rounds coordinates to two decimals", () => {
    const query = buildCaseQuery({ ...HELSINKI_CASE, places: [{ lat: 60.16952, lon: 24.93545 }] });
    expect(query).toContain("p=60.17,24.94&");
  });

  test.each([
    [44.065, "44.06"],
    [7.125, "7.12"],
    [-15.785, "-15.79"],
  ])("rounds the link coordinate %d as Python's round() does, to %s", (lon, written) => {
    const query = buildCaseQuery({ ...HELSINKI_CASE, places: [{ lat: 9.56, lon }] });
    expect(query).toContain(`p=9.56,${written}&`);
  });

  test("writes a coordinate that rounds to zero without a minus sign", () => {
    const query = buildCaseQuery({ ...HELSINKI_CASE, places: [{ lat: -0.001, lon: 24.94 }] });
    expect(query).toContain("p=0,24.94&");
  });

  test("writes no label when no place has a name", () => {
    const query = buildCaseQuery({ ...HELSINKI_CASE, places: [{ lat: 60.17, lon: 24.94 }] });
    expect(query).toBe("v=air_temp&p=60.17,24.94&from=1981&to=2025&s=annual");
  });

  test("writes an empty label for an unnamed place when another place has a name", () => {
    const query = buildCaseQuery({
      ...HELSINKI_CASE,
      places: [
        { lat: 60.17, lon: 24.94 },
        { lat: -1.29, lon: 36.82, name: "Nairobi" },
      ],
    });
    expect(query).toBe(
      "v=air_temp&p=60.17,24.94&p=-1.29,36.82&label=&label=Nairobi&from=1981&to=2025&s=annual",
    );
  });

  test("leaves out the years when they are not known", () => {
    const query = buildCaseQuery({ variable: "air_temp", places: [{ lat: 1, lon: 2 }], season: "JJA" });
    expect(query).toBe("v=air_temp&p=1,2&s=JJA");
  });

  test("writes scan=1 when the scan is asked for", () => {
    expect(buildCaseQuery({ ...HELSINKI_CASE, scan: true })).toBe(`${HELSINKI_QUERY}&scan=1`);
  });

  test("escapes characters that would break the query in a label", () => {
    const query = buildCaseQuery({
      ...HELSINKI_CASE,
      places: [{ lat: 1, lon: 2, name: "Rock & Roll #1" }],
    });
    expect(query).toContain("label=Rock%20%26%20Roll%20%231&");
  });

  test("escapes an apostrophe in a label as the browser's address bar does", () => {
    const query = buildCaseQuery({
      ...HELSINKI_CASE,
      places: [{ lat: 12.11, lon: 15.04, name: "N'Djamena" }],
    });
    expect(query).toContain("label=N%27Djamena&");
    expect(query).toBe(new URL(`http://localhost/case?${query}`).search.slice(1));
  });
});

describe("parseCaseQuery", () => {
  test("reads the example from spec section 10", () => {
    expect(parseCaseQuery(HELSINKI_QUERY)).toEqual({ ok: true, value: HELSINKI_CASE });
  });

  test("accepts a leading question mark", () => {
    expect(parseCaseQuery(`?${HELSINKI_QUERY}`)).toEqual({ ok: true, value: HELSINKI_CASE });
  });

  test("reads back every case it writes", () => {
    const params: CaseParams = {
      variable: "precipitation",
      places: [
        { lat: 60.17, lon: 24.94, name: "Helsinki, Finland" },
        { lat: -1.29, lon: 36.82 },
        { lat: 0, lon: -179.5, name: "Rock & Roll" },
      ],
      from: 1990,
      to: 2020,
      season: "DJF",
      scan: true,
    };
    expect(parseCaseQuery(buildCaseQuery(params))).toEqual({ ok: true, value: params });
  });

  test("defaults the season to annual", () => {
    const result = parseCaseQuery("v=air_temp&p=60.17,24.94");
    expect(result).toEqual({
      ok: true,
      value: { variable: "air_temp", places: [{ lat: 60.17, lon: 24.94 }], season: "annual" },
    });
  });

  test("treats an empty label as a place with no name", () => {
    const result = parseCaseQuery("v=air_temp&p=1,2&p=3,4&label=&label=Nairobi");
    expect(result.ok && result.value.places).toEqual([
      { lat: 1, lon: 2 },
      { lat: 3, lon: 4, name: "Nairobi" },
    ]);
  });

  test("accepts four places", () => {
    const result = parseCaseQuery("v=air_temp&p=1,1&p=2,2&p=3,3&p=4,4");
    expect(result.ok && result.value.places).toHaveLength(4);
  });

  test("rejects more than four places", () => {
    const reason = reasonOf(parseCaseQuery("v=air_temp&p=1,1&p=2,2&p=3,3&p=4,4&p=5,5"));
    expect(reason).toContain("at most 4 places");
  });

  test("rejects an unknown season", () => {
    expect(reasonOf(parseCaseQuery("v=air_temp&p=1,2&s=winter"))).toContain('Unknown season "winter"');
  });

  test("rejects a latitude beyond 90", () => {
    expect(reasonOf(parseCaseQuery("v=air_temp&p=91,0"))).toContain("outside the globe");
  });

  test("rejects a longitude beyond 180", () => {
    expect(reasonOf(parseCaseQuery("v=air_temp&p=0,-180.5"))).toContain("outside the globe");
  });

  test.each(["abc,1", "60.17", "1,2,3", "1,", "1e2,3", ""])(
    "rejects coordinates that are not two numbers: %j",
    (point) => {
      expect(reasonOf(parseCaseQuery(`v=air_temp&p=${point}`))).toContain("latitude,longitude");
    },
  );

  test("accepts a label of 40 characters", () => {
    expect(parseCaseQuery(`v=air_temp&p=1,2&label=${"a".repeat(40)}`).ok).toBe(true);
  });

  test("rejects a label longer than 40 characters", () => {
    const reason = reasonOf(parseCaseQuery(`v=air_temp&p=1,2&label=${"a".repeat(41)}`));
    expect(reason).toContain("at most 40 characters");
  });

  test("counts characters outside the basic plane once, as Python does", () => {
    const label = encodeURIComponent("🌍".repeat(40));
    expect(parseCaseQuery(`v=air_temp&p=1,2&label=${label}`).ok).toBe(true);
  });

  test("rejects labels that do not match the places one for one", () => {
    const reason = reasonOf(parseCaseQuery("v=air_temp&p=1,2&p=3,4&label=Helsinki"));
    expect(reason).toContain("one label for each place");
  });

  test("rejects a link with no variable", () => {
    expect(reasonOf(parseCaseQuery("p=1,2"))).toContain("does not name a variable");
  });

  test("rejects a link with no place", () => {
    expect(reasonOf(parseCaseQuery("v=air_temp"))).toContain("does not name a place");
  });

  test("rejects a year that is not a whole number", () => {
    expect(reasonOf(parseCaseQuery("v=air_temp&p=1,2&from=1981.5"))).toContain('"from" must be a year');
  });

  test.each(["0", "", " 0 "])("reads scan=%j as no scan, as the backend does", (scan) => {
    const result = parseCaseQuery(`v=air_temp&p=1,2&scan=${scan}`);
    expect(result).toEqual({
      ok: true,
      value: { variable: "air_temp", places: [{ lat: 1, lon: 2 }], season: "annual" },
    });
  });

  test("reads scan=1 as the scan", () => {
    const result = parseCaseQuery("v=air_temp&p=1,2&scan=1");
    expect(result.ok && result.value.scan).toBe(true);
  });

  test("treats an empty from, to or season as not given", () => {
    const result = parseCaseQuery("v=air_temp&p=60.17,24.94&from=&to=2025&s=");
    expect(result).toEqual({
      ok: true,
      value: { variable: "air_temp", places: [{ lat: 60.17, lon: 24.94 }], to: 2025, season: "annual" },
    });
  });

  test("trims spaces around the variable, the years and the season", () => {
    const result = parseCaseQuery("v=%20air_temp%20&p=1,2&from=%201990%20&s=%20JJA%20");
    expect(result).toEqual({
      ok: true,
      value: { variable: "air_temp", places: [{ lat: 1, lon: 2 }], from: 1990, season: "JJA" },
    });
  });

  test("trims spaces around a label", () => {
    const result = parseCaseQuery("v=air_temp&p=1,2&label=%20Helsinki%20");
    expect(result.ok && result.value.places).toEqual([{ lat: 1, lon: 2, name: "Helsinki" }]);
  });

  test("treats a label of only spaces as a place with no name", () => {
    const result = parseCaseQuery("v=air_temp&p=1,2&label=%20%20");
    expect(result.ok && result.value.places).toEqual([{ lat: 1, lon: 2 }]);
  });

  test("checks the label length after trimming, as the backend does", () => {
    expect(parseCaseQuery(`v=air_temp&p=1,2&label=%20${"a".repeat(40)}%20`).ok).toBe(true);
  });

  test("rejects a scan value other than 1", () => {
    expect(reasonOf(parseCaseQuery("v=air_temp&p=1,2&scan=yes"))).toContain('"scan" can only be 1');
  });

  test("rejects a repeated variable", () => {
    expect(reasonOf(parseCaseQuery("v=air_temp&v=precipitation&p=1,2"))).toContain("more than once");
  });

  test("leaves the years unchecked against the record, which the backend clamps", () => {
    const result = parseCaseQuery("v=air_temp&p=1,2&from=2030&to=1900");
    expect(result.ok && [result.value.from, result.value.to]).toEqual([2030, 1900]);
  });
});

describe("map query", () => {
  const MAP: MapParams = {
    variable: "air_temp",
    from: 1981,
    to: 2025,
    season: "JJA",
    box: { south: 55, west: 20, north: 65, east: 30.625 },
  };

  test("writes the variable, the period and the box, edges rounded as the backend rounds them", () => {
    expect(buildMapQuery(MAP)).toBe("v=air_temp&from=1981&to=2025&s=JJA&box=55,20,65,30.62");
  });

  test("reads back a map it writes", () => {
    const params: MapParams = { ...MAP, box: { south: -10.5, west: -75, north: -0.5, east: -65 } };
    expect(parseMapQuery(buildMapQuery(params))).toEqual({ ok: true, value: params });
  });

  test("rejects a link with no box", () => {
    expect(reasonOf(parseMapQuery("v=air_temp&s=annual"))).toContain("does not give a box");
  });

  test("rejects a box that is not four numbers", () => {
    expect(reasonOf(parseMapQuery("v=air_temp&box=1,2,3"))).toContain("four numbers");
  });

  test("rejects a box outside the globe", () => {
    expect(reasonOf(parseMapQuery("v=air_temp&box=80,0,95,10"))).toContain("outside the globe");
  });

  test("rejects an unknown season", () => {
    expect(reasonOf(parseMapQuery("v=air_temp&s=summer&box=1,2,3,4"))).toContain("Unknown season");
  });

  test("treats an empty from or season as not given", () => {
    const result = parseMapQuery("v=air_temp&from=&to=2025&s=&box=55,20,65,30");
    expect(result).toEqual({
      ok: true,
      value: {
        variable: "air_temp",
        to: 2025,
        season: "annual",
        box: { south: 55, west: 20, north: 65, east: 30 },
      },
    });
  });
});

describe("buildSeriesQuery", () => {
  test("writes the parameters of the series download", () => {
    const query = buildSeriesQuery({
      variable: "air_temp",
      place: { lat: 60.1699, lon: 24.9384 },
      from: 1981,
      to: 2025,
      season: "annual",
      resolution: "monthly",
      format: "csv",
    });
    expect(query).toBe("v=air_temp&p=60.17,24.94&from=1981&to=2025&s=annual&res=monthly&format=csv");
  });

  test("rounds the place of an investigation as the backend's link does", () => {
    const query = buildSeriesQuery({
      variable: "air_temp",
      place: { lat: 9.56, lon: 44.065 },
      from: 1981,
      to: 2025,
      season: "annual",
      resolution: "monthly",
      format: "json",
    });
    expect(query).toContain("p=9.56,44.06&");
  });
});
