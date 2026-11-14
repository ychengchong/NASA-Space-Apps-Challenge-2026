/**
 * The region types of the places in a case, such as "desert" (spec 5, PlaceCandidate, and spec 6,
 * "Places and grid cells"). Only a PlaceCandidate carries a region type, and a link holds none, so
 * the app remembers the region type of each place picked from the place list or by keyword
 * matching, and looks up the label of any other named place once.
 */

import type { PlaceCandidate } from "./api";
import { placeFromCandidate, samePoint } from "./caseDraft";
import type { CasePlace } from "./caseUrl";
import { linkCoordinate } from "./caseUrl";

/** Region types by placeKey; null records a place known to have none. */
export type RegionTypes = ReadonlyMap<string, string | null>;

/** A place's key: its link coordinates and its label, as a link to its case holds them. */
export function placeKey(place: CasePlace): string {
  return `${linkCoordinate(place.lat)},${linkCoordinate(place.lon)} ${place.name ?? ""}`;
}

/** The region type known for `place`, or null when none is known. */
export function regionTypeOf(known: RegionTypes, place: CasePlace): string | null {
  return known.get(placeKey(place)) ?? null;
}

/** The entries to remember for places picked from the place list, keyed as their cases hold them. */
export function pickedRegionTypes(candidates: readonly PlaceCandidate[]): [string, string | null][] {
  return candidates.map((candidate) => [
    placeKey(placeFromCandidate(candidate)),
    candidate.region_type ?? null,
  ]);
}

/**
 * The region type that a lookup of `place`'s label gives it. find_place has already matched the
 * label against each candidate's name and alternative names, so a candidate counts when its
 * coordinates round to the place's link coordinates, whatever its kind or name: a megacity, or
 * Svalbard for a place labelled Longyearbyen. A place of the same name elsewhere never lends its
 * type. Null when no candidate counts.
 */
export function regionTypeFromLookup(place: CasePlace, candidates: readonly PlaceCandidate[]): string | null {
  const match = candidates.find((candidate) => samePoint(candidate, place));
  return match?.region_type ?? null;
}

/** A place with a label, which a lookup can search for. */
export type NamedPlace = CasePlace & { name: string };

/**
 * The named places of `places` to look up: those whose region type is not known and that have
 * not been asked about, each once. A place with no label has nothing to look up.
 */
export function placesToLookUp(
  places: readonly CasePlace[],
  known: RegionTypes,
  asked: ReadonlySet<string>,
): NamedPlace[] {
  const toLookUp = new Map<string, NamedPlace>();
  for (const place of places) {
    const { name } = place;
    const key = placeKey(place);
    if (name === undefined || known.has(key) || asked.has(key) || toLookUp.has(key)) continue;
    toLookUp.set(key, { ...place, name });
  }
  return [...toLookUp.values()];
}

/**
 * The entry to remember for `place` after a lookup of its label. Null when the lookup fails,
 * which leaves the region type unknown, so the case simply shows no suggestions for that place;
 * the case itself does not depend on it.
 */
export function lookUpRegionType(
  place: NamedPlace,
  findPlaces: (label: string) => Promise<PlaceCandidate[]>,
): Promise<[string, string | null] | null> {
  return findPlaces(place.name).then(
    (candidates) => [placeKey(place), regionTypeFromLookup(place, candidates)],
    () => null,
  );
}
