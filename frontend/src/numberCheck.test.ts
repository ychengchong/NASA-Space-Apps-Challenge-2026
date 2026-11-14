import { describe, expect, test } from "vitest";
import { splitUnverified } from "./numberCheck";

describe("splitUnverified", () => {
  test("keeps text without unverified numbers as one plain span", () => {
    expect(splitUnverified("It rose by 0.35 °C per decade.", [])).toEqual([
      { text: "It rose by 0.35 °C per decade.", unverified: false },
    ]);
  });

  test("puts each unverified number in a span of its own", () => {
    expect(splitUnverified("It rose by 0.35 °C, not 0.5 °C.", ["0.5"])).toEqual([
      { text: "It rose by 0.35 °C, not ", unverified: false },
      { text: "0.5", unverified: true },
      { text: " °C.", unverified: false },
    ]);
  });

  test("marks every occurrence of a listed number", () => {
    const spans = splitUnverified("0.7 then 0.7", ["0.7"]);
    expect(spans.filter((span) => span.unverified).map((span) => span.text)).toEqual(["0.7", "0.7"]);
  });

  test("does not mark a listed number inside a longer number", () => {
    expect(splitUnverified("It was 21.5 here.", ["1.5"])).toEqual([
      { text: "It was 21.5 here.", unverified: false },
    ]);
  });

  test("does not mark digits that continue a word", () => {
    expect(splitUnverified("CO2 rose by 2 units.", ["2"])).toEqual([
      { text: "CO2 rose by ", unverified: false },
      { text: "2", unverified: true },
      { text: " units.", unverified: false },
    ]);
  });

  test("matches a number with its sign as the check wrote it", () => {
    expect(splitUnverified("A change of -0.3 mm.", ["-0.3"])).toEqual([
      { text: "A change of ", unverified: false },
      { text: "-0.3", unverified: true },
      { text: " mm.", unverified: false },
    ]);
  });

  test("matches a number with the typographic minus sign", () => {
    const spans = splitUnverified("A change of −0.3 mm.", ["−0.3"]);
    expect(spans[1]).toEqual({ text: "−0.3", unverified: true });
  });

  test("reads thousands separators as part of the number", () => {
    expect(splitUnverified("About 1,234 mm fell.", ["1,234"])).toEqual([
      { text: "About ", unverified: false },
      { text: "1,234", unverified: true },
      { text: " mm fell.", unverified: false },
    ]);
  });

  test("reads a number written with a leading point as one number", () => {
    expect(splitUnverified("It rose by .5 °C.", [".5"])).toEqual([
      { text: "It rose by ", unverified: false },
      { text: ".5", unverified: true },
      { text: " °C.", unverified: false },
    ]);
  });

  test("reads a number with an exponent as one number", () => {
    expect(splitUnverified("Here p = 4e-2.", ["4e-2"])).toEqual([
      { text: "Here p = ", unverified: false },
      { text: "4e-2", unverified: true },
      { text: ".", unverified: false },
    ]);
  });

  test.each(["2.5e-11", "2.5e−11", "2.5E-11"])("reads %s as one number", (written) => {
    expect(splitUnverified(`p = ${written} here`, [written])).toEqual([
      { text: "p = ", unverified: false },
      { text: written, unverified: true },
      { text: " here", unverified: false },
    ]);
  });

  test("does not read an exponent longer than three digits as one, as the check does", () => {
    expect(splitUnverified("Say 1e-9999 here.", ["9999"])).toEqual([
      { text: "Say 1e-", unverified: false },
      { text: "9999", unverified: true },
      { text: " here.", unverified: false },
    ]);
  });

  test("marks a number at the very start and end of the text", () => {
    expect(splitUnverified("12 or 13", ["12", "13"])).toEqual([
      { text: "12", unverified: true },
      { text: " or ", unverified: false },
      { text: "13", unverified: true },
    ]);
  });

  test("gives back the whole text when the spans are joined", () => {
    const text = "From 1981 to 2025 it rose by 0.48 °C per decade, about 2.1 °C in all.";
    const joined = splitUnverified(text, ["2.1", "0.48"])
      .map((span) => span.text)
      .join("");
    expect(joined).toBe(text);
  });

  test("gives no spans for empty text", () => {
    expect(splitUnverified("", ["1"])).toEqual([]);
  });
});
