import { describe, expect, test } from "vitest";
import { NEUTRAL_COLOUR, scaleEndDecimals, scaleGradient, scaleLimit, slopeColour } from "./colourScale";
import { formatSignedRate } from "./format";

function redMinusBlue(hex: string): number {
  return parseInt(hex.slice(1, 3), 16) - parseInt(hex.slice(5, 7), 16);
}

function brightness(hex: string): number {
  return [1, 3, 5].reduce((sum, offset) => sum + parseInt(hex.slice(offset, offset + 2), 16), 0);
}

describe("slopeColour", () => {
  test("colours a zero rate neutral", () => {
    expect(slopeColour(0, 1)).toBe(NEUTRAL_COLOUR);
  });

  test("colours a rise red and a fall blue", () => {
    expect(redMinusBlue(slopeColour(0.5, 1))).toBeGreaterThan(0);
    expect(redMinusBlue(slopeColour(-0.5, 1))).toBeLessThan(0);
  });

  test("darkens as the size of the rate grows", () => {
    expect(brightness(slopeColour(0.9, 1))).toBeLessThan(brightness(slopeColour(0.3, 1)));
    expect(brightness(slopeColour(-0.9, 1))).toBeLessThan(brightness(slopeColour(-0.3, 1)));
  });

  test("gives the ends of the scale its darkest colours", () => {
    expect(slopeColour(1, 1)).toBe("#762221");
    expect(slopeColour(-1, 1)).toBe("#104281");
  });

  test("clamps a rate beyond the scale to the colour of its end", () => {
    expect(slopeColour(5, 1)).toBe(slopeColour(1, 1));
    expect(slopeColour(-5, 1)).toBe(slopeColour(-1, 1));
  });

  test("hits each colour stop exactly", () => {
    expect(slopeColour(0.25, 1)).toBe("#f1aea8");
    expect(slopeColour(-0.5, 1)).toBe("#5598e7");
  });

  test("colours everything neutral when the scale has no size", () => {
    expect(slopeColour(0.4, 0)).toBe(NEUTRAL_COLOUR);
  });

  test("always returns a six-digit hex colour", () => {
    for (const slope of [-1.3, -0.61, -0.07, 0.07, 0.61, 1.3]) {
      expect(slopeColour(slope, 1)).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
});

describe("scaleLimit", () => {
  test("rounds the largest size up to a nice number", () => {
    expect(scaleLimit([0.2, -0.734, 0.5])).toBe(0.8);
  });

  test("counts a fall as large as a rise", () => {
    expect(scaleLimit([0.1, -2.6])).toBe(3);
  });

  test("keeps a size that is already nice", () => {
    expect(scaleLimit([0.25])).toBe(0.25);
  });

  test("skips missing rates", () => {
    expect(scaleLimit([null, 0.06, null])).toBe(0.06);
  });

  test("is zero when there is no rate or every rate is zero", () => {
    expect(scaleLimit([])).toBe(0);
    expect(scaleLimit([null])).toBe(0);
    expect(scaleLimit([0, 0])).toBe(0);
  });
});

describe("scaleEndDecimals", () => {
  test("adds the digits a scale end needs to be written exactly", () => {
    expect(scaleEndDecimals(0.15, 1)).toBe(2);
    expect(scaleEndDecimals(0.025, 2)).toBe(3);
    expect(scaleEndDecimals(0.0015, 3)).toBe(4);
  });

  test("never gives fewer digits than the variable's own", () => {
    expect(scaleEndDecimals(3, 1)).toBe(1);
    expect(scaleEndDecimals(0.8, 2)).toBe(2);
  });

  test("lets the legend write the end of the scale that the colours use", () => {
    const limit = scaleLimit([0.14, 0.02]);
    expect(formatSignedRate(limit, scaleEndDecimals(limit, 1))).toBe("+0.15");
  });
});

describe("scaleGradient", () => {
  test("runs from the darkest blue through neutral to the darkest red", () => {
    const gradient = scaleGradient();
    expect(gradient.startsWith("linear-gradient(to right, #104281")).toBe(true);
    expect(gradient).toContain(NEUTRAL_COLOUR);
    expect(gradient.endsWith("#762221)")).toBe(true);
  });
});
