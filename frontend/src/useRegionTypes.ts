/**
 * The region types the app knows for places (regionTypes.ts), for the session. A place picked
 * from the place list brings its own; each other named place of an open case is looked up once.
 */

import { useEffect, useEffectEvent, useRef, useState } from "react";
import { getPlaces } from "./api";
import type { PlaceCandidate } from "./api";
import type { CasePlace } from "./caseUrl";
import { lookUpRegionType, pickedRegionTypes, placeKey, placesToLookUp } from "./regionTypes";
import type { RegionTypes } from "./regionTypes";

export interface RegionTypeMemory {
  known: RegionTypes;
  /** Records the region types of places picked from the place list or by keyword matching. */
  remember: (candidates: readonly PlaceCandidate[]) => void;
}

/** Looks up, once each, the labels of the places in `casePlaces` whose region type is not known. */
export function useRegionTypes(casePlaces: readonly CasePlace[]): RegionTypeMemory {
  const [known, setKnown] = useState<RegionTypes>(() => new Map());
  // Labels asked about already, so a place is looked up once even while its answer is on the way.
  const askedRef = useRef(new Set<string>());
  const lookUpNewPlaces = useEffectEvent((places: readonly CasePlace[]) => {
    for (const place of placesToLookUp(places, known, askedRef.current)) {
      askedRef.current.add(placeKey(place));
      void lookUpRegionType(place, getPlaces).then((entry) => {
        if (entry !== null) setKnown((map) => withEntries(map, [entry]));
      });
    }
  });

  useEffect(() => lookUpNewPlaces(casePlaces), [casePlaces]);

  const remember = (candidates: readonly PlaceCandidate[]): void => {
    setKnown((map) => withEntries(map, pickedRegionTypes(candidates)));
  };
  return { known, remember };
}

function withEntries(map: RegionTypes, entries: readonly [string, string | null][]): RegionTypes {
  return new Map([...map, ...entries]);
}
