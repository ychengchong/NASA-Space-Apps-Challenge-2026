/**
 * The mapping between the address bar and what the app shows (spec 10, "Case parameters").
 * `/case?...` opens a case, `/map?...` the region view, and every other path the first screen.
 */

import type { Requested } from "./api";
import { buildCaseQuery, buildMapQuery, parseCaseQuery } from "./caseUrl";
import type { CaseParams, MapParams } from "./caseUrl";

export const HOME_PATH = "/";
export const CASE_PATH = "/case";
export const MAP_PATH = "/map";

export type Route =
  | { kind: "home" }
  | { kind: "case"; params: CaseParams }
  /** `query` is the map's parameter string, without the leading "?". */
  | { kind: "map"; query: string }
  /** A case link the app cannot read; `reason` is a sentence for the user. */
  | { kind: "bad_link"; reason: string };

/** The route for a page address, given as `location.pathname` and `location.search`. */
export function parseRoute(pathname: string, search: string): Route {
  const path = withoutTrailingSlash(pathname);
  if (path === CASE_PATH) {
    const parsed = parseCaseQuery(search);
    if (!parsed.ok) return { kind: "bad_link", reason: parsed.reason };
    return { kind: "case", params: withoutScan(parsed.value) };
  }
  if (path === MAP_PATH) return { kind: "map", query: search.replace(/^\?/, "") };
  return { kind: "home" };
}

/** The page address of a case. */
export function casePageUrl(params: CaseParams): string {
  return `${CASE_PATH}?${buildCaseQuery(withoutScan(params))}`;
}

/** The page address of a map. */
export function mapPageUrl(params: MapParams): string {
  return `${MAP_PATH}?${buildMapQuery(params)}`;
}

/**
 * The query string of an `app_url` from the API, without its "?", or "" when it has none. The
 * API's link may carry the public host name, so only its parameters are used inside the app.
 */
export function appUrlQuery(appUrl: string): string {
  const start = appUrl.indexOf("?");
  return start === -1 ? "" : appUrl.slice(start + 1);
}

/** The page address of an example case, whose `query` is a case's parameter string. */
export function examplePageUrl(query: string): string {
  return `${CASE_PATH}?${query.replace(/^\?/, "")}`;
}

/**
 * The case with the period the API actually used. Spec 10: the address bar always holds `from`,
 * `to` and `s`, clamped to the record, so a link keeps its meaning as the record grows.
 */
export function withRequestedPeriod(params: CaseParams, requested: Requested): CaseParams {
  return {
    ...withoutScan(params),
    from: requested.from,
    to: requested.to,
    season: requested.season,
  };
}

/** True when two cases have the same parameter string. */
export function sameCase(a: CaseParams, b: CaseParams): boolean {
  return buildCaseQuery(withoutScan(a)) === buildCaseQuery(withoutScan(b));
}

// The scan is a display option of the period explorer, not part of the case, so it never
// appears in the address bar.
function withoutScan(params: CaseParams): CaseParams {
  const copy = { ...params };
  delete copy.scan;
  return copy;
}

function withoutTrailingSlash(pathname: string): string {
  return pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
}
