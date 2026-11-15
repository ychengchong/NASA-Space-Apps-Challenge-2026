/**
 * The example cases as the first screen's globe shows them (spec 3, "The globe"): a numbered pin
 * at each place a case tests. Nothing here needs a browser.
 */

import type { ExampleCase } from "./api";
import { parseCaseQuery } from "./caseUrl";
import { formatCoordinates } from "./format";
import type { MapPlace } from "./mapCell";
import { examplePageUrl } from "./route";

/** An example case to pin to the globe. */
export interface ExamplePin {
  /** The case's number in the list of examples, from 1. */
  number: number;
  title: string;
  /** The address of the case's page. */
  url: string;
  /** The places the case tests, in the case's own order. */
  places: readonly MapPlace[];
}

/** One example singled out on the globe. */
export interface ExampleLink {
  number: number;
  /**
   * True when the Earth turns to face the example's places, as it does for an example chosen in
   * the list. False for one whose pin the pointer is on, so the pin stays under the pointer.
   */
  turn: boolean;
}

/** Who hears what the user does with the pins of the examples. */
export interface ExampleListeners {
  /** The user clicked or tapped a pin of this case. */
  onOpen: (pin: ExamplePin) => void;
  /** The pointer is on a pin of this case, or, with null, has left it. */
  onPoint: (pin: ExamplePin | null) => void;
}

/**
 * The pins of the examples, numbered as the list numbers them. An example whose link does not
 * open a case has no pin, and the others keep their numbers.
 */
export function examplePins(examples: readonly ExampleCase[]): ExamplePin[] {
  const pins: ExamplePin[] = [];
  examples.forEach((example, index) => {
    const parsed = parseCaseQuery(example.query);
    if (!parsed.ok) return;
    pins.push({
      number: index + 1,
      title: example.title,
      url: examplePageUrl(example.query),
      places: parsed.value.places.map((place) => ({
        name: place.name ?? formatCoordinates(place.lat, place.lon),
        lat: place.lat,
        lon: place.lon,
      })),
    });
  });
  return pins;
}

/**
 * The example that is singled out once the pointer is on a pin of `pin`'s case, or, with null,
 * has left a pin. The Earth does not turn to a case pointed at on the globe. Leaving a pin lets
 * go only of a case that a pin singled out, so one chosen in the list stays.
 */
export function pointedExample(current: ExampleLink | null, pin: ExamplePin | null): ExampleLink | null {
  if (pin !== null) return { number: pin.number, turn: false };
  return current !== null && !current.turn ? null : current;
}

/**
 * Which of the pin's places carries the card with the case's question: the northernmost. The
 * card stands above its pin and north is always up, so it covers none of the case's other pins.
 */
export function cardPlaceIndex(pin: ExamplePin): number {
  let northernmost = 0;
  pin.places.forEach((place, index) => {
    if (place.lat > (pin.places[northernmost]?.lat ?? place.lat)) northernmost = index;
  });
  return northernmost;
}
