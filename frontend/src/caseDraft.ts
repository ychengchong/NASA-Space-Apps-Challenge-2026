/**
 * The case settings while the user edits them. A draft may be incomplete, such as a case with no
 * place yet; only a complete draft becomes a case (spec 3, "The investigation flow").
 */

import type { PlaceCandidate, Season } from "./api";
import { linkCoordinate, MAX_PLACES, PLACE_LABEL_MAX_LENGTH } from "./caseUrl";
import type { CaseParams, CasePlace } from "./caseUrl";
import { formatCoordinates } from "./format";
import type { KeywordProposal } from "./keywordMatch";

export interface CaseDraft {
  variable: string | null;
  places: CasePlace[];
  from?: number;
  to?: number;
  season: Season;
}

export const EMPTY_DRAFT: CaseDraft = { variable: null, places: [], season: "annual" };

/** The settings of an open case, without the display-only scan option. */
export function draftFromCase(params: CaseParams): CaseDraft {
  const draft: CaseDraft = {
    variable: params.variable,
    places: params.places,
    season: params.season,
  };
  if (params.from !== undefined) draft.from = params.from;
  if (params.to !== undefined) draft.to = params.to;
  return draft;
}

/** The case a draft describes, or null while it lacks a variable or a place. */
export function caseFromDraft(draft: CaseDraft): CaseParams | null {
  if (draft.variable === null || draft.places.length === 0) return null;
  const params: CaseParams = {
    variable: draft.variable,
    places: draft.places,
    season: draft.season,
  };
  if (draft.from !== undefined) params.from = draft.from;
  if (draft.to !== undefined) params.to = draft.to;
  return params;
}

/**
 * What a chosen place can do to the draft: become its first place ("use"), take the place of its
 * only place ("replace"), or join the places to compare ("compare" next to one place, "add" to
 * two or three). A place already in the draft, or a fifth place, has no action.
 */
export type PlaceAction = "use" | "replace" | "compare" | "add";

export function placeActions(places: readonly CasePlace[], candidate: CasePlace): PlaceAction[] {
  if (places.length === 0) return ["use"];
  if (places.some((place) => samePoint(place, candidate))) return [];
  if (places.length === 1) return ["replace", "compare"];
  if (places.length < MAX_PLACES) return ["add"];
  return [];
}

export function applyPlaceAction(draft: CaseDraft, action: PlaceAction, place: CasePlace): CaseDraft {
  if (action === "use" || action === "replace") return { ...draft, places: [place] };
  return { ...draft, places: [...draft.places, place] };
}

export function removePlace(draft: CaseDraft, index: number): CaseDraft {
  return { ...draft, places: draft.places.filter((_, position) => position !== index) };
}

/** True when two points share the link coordinates, so they open the same grid cell. */
export function samePoint(a: CasePlace, b: CasePlace): boolean {
  return linkCoordinate(a.lat) === linkCoordinate(b.lat) && linkCoordinate(a.lon) === linkCoordinate(b.lon);
}

/** The name the settings show for a place: its label, or its coordinates when it has none. */
export function placeName(place: CasePlace): string {
  return place.name ?? formatCoordinates(place.lat, place.lon);
}

/** A place from the place list, labelled with its name cut to the label limit of spec 10. */
export function placeFromCandidate(candidate: PlaceCandidate): CasePlace {
  // Count characters as Python's len() does, as caseUrl.ts does for the same limit.
  const name = [...candidate.name].slice(0, PLACE_LABEL_MAX_LENGTH).join("");
  return { lat: candidate.lat, lon: candidate.lon, name };
}

/**
 * The draft after a keyword match: the best variable and the places found replace those of
 * `base`, and whatever the question did not name stays as it was.
 */
export function draftFromProposal(base: CaseDraft, proposal: KeywordProposal): CaseDraft {
  const variable = proposal.variables[0]?.id ?? base.variable;
  const places =
    proposal.places.length > 0 ? proposal.places.slice(0, MAX_PLACES).map(placeFromCandidate) : base.places;
  return { ...base, variable, places };
}

const YEAR_TEXT = /^\d{4}$/;

/**
 * A year typed into a period box: a number for four digits, undefined for an empty box (the full
 * record), or "invalid" for anything else.
 */
export function parseYearText(text: string): number | undefined | "invalid" {
  const trimmed = text.trim();
  if (trimmed === "") return undefined;
  return YEAR_TEXT.test(trimmed) ? Number(trimmed) : "invalid";
}
