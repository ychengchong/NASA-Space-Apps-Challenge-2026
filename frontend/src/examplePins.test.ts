import { describe, expect, test } from "vitest";
import { cardPlaceIndex, examplePins, pointedExample } from "./examplePins";

const SVALBARD = {
  title: "Is Svalbard getting warmer?",
  teaser: "Air temperature in Longyearbyen.",
  query: "v=air_temp&p=78.22,15.65&label=Longyearbyen&from=1981&to=2025&s=annual",
};
const TWO_CITIES = {
  title: "Rain in Athens and Helsinki",
  teaser: "Two cities, one variable.",
  query: "v=precipitation&p=37.98,23.73&p=60.17,24.94&label=Athens&label=Helsinki&from=1981&to=2025&s=annual",
};

describe("examplePins", () => {
  test("gives each example its number in the list, its page and its places by name", () => {
    expect(examplePins([SVALBARD, TWO_CITIES])).toEqual([
      {
        number: 1,
        title: "Is Svalbard getting warmer?",
        url: `/case?${SVALBARD.query}`,
        places: [{ name: "Longyearbyen", lat: 78.22, lon: 15.65 }],
      },
      {
        number: 2,
        title: "Rain in Athens and Helsinki",
        url: `/case?${TWO_CITIES.query}`,
        places: [
          { name: "Athens", lat: 37.98, lon: 23.73 },
          { name: "Helsinki", lat: 60.17, lon: 24.94 },
        ],
      },
    ]);
  });

  test("names a place without a label by its coordinates", () => {
    const [pin] = examplePins([{ ...SVALBARD, query: "v=air_temp&p=-1.29,36.82&s=annual" }]);
    expect(pin?.places).toEqual([{ name: "1.3°S, 36.8°E", lat: -1.29, lon: 36.82 }]);
  });

  test("leaves out an example whose link does not open a case, and keeps the others' numbers", () => {
    const broken = { ...SVALBARD, query: "v=air_temp&p=not-a-place" };
    expect(examplePins([broken, TWO_CITIES]).map((pin) => pin.number)).toEqual([2]);
  });
});

describe("pointedExample", () => {
  const [svalbard] = examplePins([SVALBARD]);
  if (svalbard === undefined) throw new Error("The example has no pin.");

  test("singles out the case of the pin under the pointer, without turning the Earth", () => {
    expect(pointedExample(null, svalbard)).toEqual({ number: 1, turn: false });
  });

  test("takes over from an example singled out in the list", () => {
    expect(pointedExample({ number: 2, turn: true }, svalbard)).toEqual({ number: 1, turn: false });
  });

  test("lets go of the case once the pointer has left its pin", () => {
    expect(pointedExample({ number: 1, turn: false }, null)).toBeNull();
  });

  test("keeps an example singled out in the list when the pointer leaves a pin", () => {
    expect(pointedExample({ number: 2, turn: true }, null)).toEqual({ number: 2, turn: true });
  });
});

describe("cardPlaceIndex", () => {
  test("is the northernmost place, wherever it stands in the case", () => {
    const [, twoCities] = examplePins([SVALBARD, TWO_CITIES]);
    if (twoCities === undefined) throw new Error("The example has no pin.");
    expect(cardPlaceIndex(twoCities)).toBe(1);
    expect(cardPlaceIndex({ ...twoCities, places: [...twoCities.places].reverse() })).toBe(0);
  });

  test("is the only place of a case that tests one", () => {
    const [svalbard] = examplePins([SVALBARD]);
    if (svalbard === undefined) throw new Error("The example has no pin.");
    expect(cardPlaceIndex(svalbard)).toBe(0);
  });
});
