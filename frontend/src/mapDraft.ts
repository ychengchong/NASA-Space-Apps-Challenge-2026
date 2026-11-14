/**
 * The map settings while the user edits them (spec 10, `/map`). The boxes hold text, so a half-typed
 * number stays as typed; only a complete draft becomes a map.
 */

import type { Box, Season } from "./api";
import { parseYearText } from "./caseDraft";
import { buildMapQuery, parseMapQuery } from "./caseUrl";
import type { MapParams, ParseResult } from "./caseUrl";

export type BoxText = Record<keyof Box, string>;

export interface MapDraft {
  variable: string | null;
  fromText: string;
  toText: string;
  season: Season;
  box: BoxText;
}

export const EMPTY_MAP_DRAFT: MapDraft = {
  variable: null,
  fromText: "",
  toText: "",
  season: "annual",
  box: { south: "", west: "", north: "", east: "" },
};

const BOX_SIDES: readonly (keyof Box)[] = ["south", "west", "north", "east"];

/** The draft of a map page's query string, or the empty draft when the query is not a map. */
export function draftFromMapQuery(query: string): MapDraft {
  const parsed = parseMapQuery(query);
  if (!parsed.ok) return EMPTY_MAP_DRAFT;
  const { variable, from, to, season, box } = parsed.value;
  return {
    variable,
    fromText: from === undefined ? "" : String(from),
    toText: to === undefined ? "" : String(to),
    season,
    box: boxText(box),
  };
}

export function boxText(box: Box): BoxText {
  return {
    south: String(box.south),
    west: String(box.west),
    north: String(box.north),
    east: String(box.east),
  };
}

/**
 * The map a draft describes, or a sentence saying what to fix. Whether the box is small enough
 * is left to the API, whose message names its own limits.
 */
export function mapFromDraft(draft: MapDraft): ParseResult<MapParams> {
  if (draft.variable === null) return invalid("Choose a variable.");
  const from = parseYearText(draft.fromText);
  const to = parseYearText(draft.toText);
  if (from === "invalid" || to === "invalid") {
    return invalid("Enter a year with four digits, such as 1990, or leave the box empty.");
  }
  if (from !== undefined && to !== undefined && from > to) {
    return invalid("The first year must not be later than the last year.");
  }
  const box = parseBoxText(draft.box);
  if (box === null) return invalid("Enter each edge of the box as a number of degrees, such as 55 or -12.5.");

  const params: MapParams = { variable: draft.variable, season: draft.season, box };
  if (from !== undefined) params.from = from;
  if (to !== undefined) params.to = to;
  // The page reads its address back with parseMapQuery, so a draft it would refuse is refused here.
  const reread = parseMapQuery(buildMapQuery(params));
  return reread.ok ? reread : invalid(reread.reason);
}

function parseBoxText(text: BoxText): Box | null {
  const box: Partial<Box> = {};
  for (const side of BOX_SIDES) {
    const trimmed = text[side].trim();
    const value = Number(trimmed);
    if (trimmed === "" || !Number.isFinite(value)) return null;
    box[side] = value;
  }
  const { south, west, north, east } = box;
  if (south === undefined || west === undefined || north === undefined || east === undefined) return null;
  return { south, west, north, east };
}

function invalid(reason: string): ParseResult<MapParams> {
  return { ok: false, reason };
}
