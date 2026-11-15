import { describe, expect, test } from "vitest";
import { isScrolledPast } from "./useScrolledPast";

describe("isScrolledPast", () => {
  test("is true once the whole element lies above the top of the screen", () => {
    expect(isScrolledPast(false, -12)).toBe(true);
    expect(isScrolledPast(false, 0)).toBe(true);
  });

  test("is false while any of the element shows", () => {
    expect(isScrolledPast(true, 40)).toBe(false);
  });

  test("is false for an element below the screen, which the page has not reached", () => {
    expect(isScrolledPast(false, 1400)).toBe(false);
  });
});
