/**
 * Variables to test next in an open case (spec 3, "The investigation flow", step 6): the
 * variable's related variables, curated in the catalogue as cross-checks, and the variables worth
 * testing in the region type of a place in the case. A suggestion keeps the case's places, period
 * and season and switches the variable.
 */

import type { VariableSummary } from "./api";
import type { CaseParams, CasePlace } from "./caseUrl";
import { formatCoordinates } from "./format";

/** The case with another variable; its places, period and season stay. */
export function withVariable(params: CaseParams, variable: string): CaseParams {
  const next = { ...params, variable };
  delete next.snapshotIds;
  delete next.analysisVersion;
  return next;
}

/** The catalogue entries of `variable.related`, in that order; an id not in the catalogue is left out. */
export function relatedVariables(
  variable: VariableSummary,
  catalogue: readonly VariableSummary[],
): VariableSummary[] {
  return variable.related.flatMap((id) => catalogue.filter((entry) => entry.id === id));
}

export interface RegionTypeSuggestion {
  regionType: string;
  /** The names of the case's places of this region type, in the case's order. */
  placeNames: string[];
  /** The variables worth testing there, in catalogue order, without the case's own variable. */
  variables: VariableSummary[];
}

/**
 * One suggestion for each region type known among `places`, in the order of the places. A place
 * whose region type is not known gives none, and so does a region type with no variable worth
 * testing other than `variable` itself.
 */
export function regionTypeSuggestions(
  places: readonly CasePlace[],
  regionTypeOf: (place: CasePlace) => string | null,
  catalogue: readonly VariableSummary[],
  variable: VariableSummary,
): RegionTypeSuggestion[] {
  const suggestions: RegionTypeSuggestion[] = [];
  for (const place of places) {
    const regionType = regionTypeOf(place);
    if (regionType === null) continue;
    const name = place.name ?? formatCoordinates(place.lat, place.lon);
    const known = suggestions.find((suggestion) => suggestion.regionType === regionType);
    if (known !== undefined) {
      known.placeNames.push(name);
      continue;
    }
    const variables = catalogue.filter(
      (entry) => entry.id !== variable.id && entry.region_types?.includes(regionType) === true,
    );
    if (variables.length > 0) suggestions.push({ regionType, placeNames: [name], variables });
  }
  return suggestions;
}
