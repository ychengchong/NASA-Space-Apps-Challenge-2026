/**
 * The mapping between a case, or a map, and the query string of its page and API call
 * (spec 10, "Case parameters"). The page and the API call share one parameter string.
 */

import type { Box, Resolution, Season, SeriesFormat } from "./api";
import { formatNumber } from "./format";

// Spec 10: a case holds up to four places.
export const MAX_PLACES = 4;
// Spec 5 and 10: a place label is display text of at most 40 characters.
export const PLACE_LABEL_MAX_LENGTH = 40;
// Spec 10 and 11: coordinates in a link are rounded to two decimals.
const LINK_COORDINATE_DECIMALS = 2;
// Spec 5: latitude runs from -90 to 90 and longitude from -180 to 180.
const MAX_LATITUDE = 90;
const MAX_LONGITUDE = 180;
// Spec 10: `s` defaults to annual.
const DEFAULT_SEASON: Season = "annual";
// Spec 10: `scan=1` asks for the scan, and `0` or empty leaves it out.
const SCAN_ON = "1";
const SCAN_OFF = "0";

// A Record, so the compiler checks that every Season is listed and nothing else is.
const SEASONS: Record<Season, true> = { annual: true, DJF: true, MAM: true, JJA: true, SON: true };

const DECIMAL_NUMBER = /^[-+]?(?:\d+(?:\.\d*)?|\.\d+)$/;
const WHOLE_NUMBER = /^\d+$/;

export interface PeriodParams {
  from?: number;
  to?: number;
  season: Season;
}

export interface CasePlace {
  lat: number;
  lon: number;
  name?: string;
}

export interface CaseParams extends PeriodParams {
  variable: string;
  places: CasePlace[];
  scan?: boolean;
}

export interface MapParams extends PeriodParams {
  variable: string;
  box: Box;
}

export interface SeriesParams extends PeriodParams {
  variable: string;
  place: { lat: number; lon: number };
  resolution: Resolution;
  format: SeriesFormat;
}

interface Invalid {
  ok: false;
  /** A plain sentence that can be shown to the user. */
  reason: string;
}

export type ParseResult<T> = { ok: true; value: T } | Invalid;

type QueryEntry = readonly [name: string, value: string];

/**
 * Writes `v`, one `p` per place, `label` when any place has a name, `from` and `to` when known,
 * `s`, and `scan=1` when the scan is asked for.
 */
export function buildCaseQuery(params: CaseParams): string {
  const entries: QueryEntry[] = [["v", params.variable]];
  for (const place of params.places) entries.push(["p", pointParam(place)]);
  if (params.places.some((place) => hasName(place))) {
    for (const place of params.places) entries.push(["label", place.name ?? ""]);
  }
  entries.push(...periodEntries(params));
  if (params.scan === true) entries.push(["scan", "1"]);
  return encodeQuery(entries);
}

/** Reads a case page's query string, with or without its leading "?". */
export function parseCaseQuery(query: string): ParseResult<CaseParams> {
  const search = new URLSearchParams(query);
  const variable = parseVariable(search);
  if (!variable.ok) return variable;
  const places = parsePlaces(search);
  if (!places.ok) return places;
  const period = parsePeriod(search);
  if (!period.ok) return period;
  const scan = parseScan(search);
  if (!scan.ok) return scan;

  const params: CaseParams = { variable: variable.value, places: places.value, ...period.value };
  if (scan.value) params.scan = true;
  return valid(params);
}

/** Writes `v`, `from` and `to` when known, `s`, and `box=south,west,north,east`. */
export function buildMapQuery(params: MapParams): string {
  const { south, west, north, east } = params.box;
  const box = [south, west, north, east].map(roundCoordinate).join(",");
  return encodeQuery([["v", params.variable], ...periodEntries(params), ["box", box]]);
}

/** Reads a map page's query string, with or without its leading "?". */
export function parseMapQuery(query: string): ParseResult<MapParams> {
  const search = new URLSearchParams(query);
  const variable = parseVariable(search);
  if (!variable.ok) return variable;
  const period = parsePeriod(search);
  if (!period.ok) return period;
  const box = parseBox(search);
  if (!box.ok) return box;
  return valid({ variable: variable.value, ...period.value, box: box.value });
}

/** Writes the parameters of `/api/series`: `v`, one `p`, `from`, `to`, `s`, `res` and `format`. */
export function buildSeriesQuery(params: SeriesParams): string {
  return encodeQuery([
    ["v", params.variable],
    ["p", pointParam(params.place)],
    ...periodEntries(params),
    ["res", params.resolution],
    ["format", params.format],
  ]);
}

function periodEntries(period: PeriodParams): QueryEntry[] {
  const entries: QueryEntry[] = [];
  if (period.from !== undefined) entries.push(["from", String(period.from)]);
  if (period.to !== undefined) entries.push(["to", String(period.to)]);
  entries.push(["s", period.season]);
  return entries;
}

function hasName(place: CasePlace): boolean {
  return place.name !== undefined && place.name !== "";
}

function pointParam(point: { lat: number; lon: number }): string {
  return `${roundCoordinate(point.lat)},${roundCoordinate(point.lon)}`;
}

/**
 * A coordinate rounded to two decimals, as the backend rounds it before snapping to the grid
 * (spec 11). An exact tie goes to the even digit, as Python's round() does, so the app and the
 * backend open the same grid cell for the same point.
 */
export function linkCoordinate(value: number): number {
  return Number(formatNumber(value, LINK_COORDINATE_DECIMALS));
}

function roundCoordinate(value: number): string {
  return String(linkCoordinate(value));
}

function encodeQuery(entries: readonly QueryEntry[]): string {
  return entries.map(([name, value]) => `${name}=${encodeValue(value)}`).join("&");
}

// A query string needs no escape for commas, so links keep the readable form of spec 10,
// such as p=60.17,24.94. Browsers and the API's own links escape an apostrophe in a query, so it
// is escaped here too, and a link the app writes matches the address bar character for character.
function encodeValue(value: string): string {
  return encodeURIComponent(value).replaceAll("%2C", ",").replaceAll("'", "%27");
}

function parseVariable(search: URLSearchParams): ParseResult<string> {
  const variable = single(search, "v");
  if (!variable.ok) return variable;
  if (variable.value === undefined) return invalid("The link does not name a variable.");
  return valid(variable.value);
}

function parsePlaces(search: URLSearchParams): ParseResult<CasePlace[]> {
  const points = search.getAll("p");
  const labels = search.getAll("label");
  if (points.length === 0) return invalid("The link does not name a place.");
  if (points.length > MAX_PLACES) {
    return invalid(`A case can hold at most ${MAX_PLACES} places, but the link has ${points.length}.`);
  }
  if (labels.length > 0 && labels.length !== points.length) {
    return invalid("The link must give one label for each place, or no labels at all.");
  }

  const places: CasePlace[] = [];
  for (const [index, text] of points.entries()) {
    const point = parsePoint(text);
    if (!point.ok) return point;
    // Trimmed before the length check, and blank means no name, as the backend reads labels.
    const label = (labels[index] ?? "").trim();
    // Count characters as Python's len() does, so the limit matches the backend's check.
    if ([...label].length > PLACE_LABEL_MAX_LENGTH) {
      return invalid(`A place label can be at most ${PLACE_LABEL_MAX_LENGTH} characters long.`);
    }
    places.push(label === "" ? point.value : { ...point.value, name: label });
  }
  return valid(places);
}

function parsePoint(text: string): ParseResult<{ lat: number; lon: number }> {
  const [lat, lon, ...rest] = text.split(",").map(parseDecimal);
  if (lat === undefined || lon === undefined || rest.length > 0) {
    return invalid(`"${text}" is not a place written as latitude,longitude.`);
  }
  if (!isLatitude(lat) || !isLongitude(lon)) {
    return invalid(
      `"${text}" is outside the globe: latitude must be from -${MAX_LATITUDE} to ${MAX_LATITUDE} ` +
        `and longitude from -${MAX_LONGITUDE} to ${MAX_LONGITUDE}.`,
    );
  }
  return valid({ lat, lon });
}

function parseBox(search: URLSearchParams): ParseResult<Box> {
  const text = single(search, "box");
  if (!text.ok) return text;
  if (text.value === undefined) return invalid("The link does not give a box.");

  const [south, west, north, east, ...rest] = text.value.split(",").map(parseDecimal);
  if (
    south === undefined ||
    west === undefined ||
    north === undefined ||
    east === undefined ||
    rest.length > 0
  ) {
    return invalid("The box must be four numbers: south,west,north,east.");
  }
  if (!isLatitude(south) || !isLatitude(north) || !isLongitude(west) || !isLongitude(east)) {
    return invalid("The box reaches outside the globe.");
  }
  return valid({ south, west, north, east });
}

function parsePeriod(search: URLSearchParams): ParseResult<PeriodParams> {
  const from = parseYear(search, "from");
  if (!from.ok) return from;
  const to = parseYear(search, "to");
  if (!to.ok) return to;
  const season = single(search, "s");
  if (!season.ok) return season;

  const seasonText = season.value ?? DEFAULT_SEASON;
  if (!isSeason(seasonText)) {
    return invalid(`Unknown season "${seasonText}". Use annual, DJF, MAM, JJA or SON.`);
  }
  return valid({ from: from.value, to: to.value, season: seasonText });
}

function parseYear(search: URLSearchParams, name: "from" | "to"): ParseResult<number | undefined> {
  const year = single(search, name);
  if (!year.ok) return year;
  if (year.value === undefined) return valid(undefined);
  if (!WHOLE_NUMBER.test(year.value)) {
    return invalid(`"${name}" must be a year, such as 1981, not "${year.value}".`);
  }
  return valid(Number(year.value));
}

function parseScan(search: URLSearchParams): ParseResult<boolean> {
  const scan = single(search, "scan");
  if (!scan.ok) return scan;
  if (scan.value === undefined || scan.value === SCAN_OFF) return valid(false);
  if (scan.value !== SCAN_ON) return invalid(`"scan" can only be 1 or 0, not "${scan.value}".`);
  return valid(true);
}

/**
 * Reads a parameter that may appear at most once, trimmed. A blank value counts as not given,
 * as the backend's case_query.py reads it.
 */
function single(search: URLSearchParams, name: string): ParseResult<string | undefined> {
  const values = search.getAll(name);
  if (values.length > 1) return invalid(`The link gives "${name}" more than once.`);
  const value = values[0]?.trim();
  return valid(value === "" ? undefined : value);
}

function parseDecimal(text: string): number | undefined {
  const trimmed = text.trim();
  return DECIMAL_NUMBER.test(trimmed) ? Number(trimmed) : undefined;
}

function isLatitude(value: number): boolean {
  return Math.abs(value) <= MAX_LATITUDE;
}

function isLongitude(value: number): boolean {
  return Math.abs(value) <= MAX_LONGITUDE;
}

function isSeason(value: string): value is Season {
  return Object.hasOwn(SEASONS, value);
}

function valid<T>(value: T): ParseResult<T> {
  return { ok: true, value };
}

function invalid(reason: string): Invalid {
  return { ok: false, reason };
}
