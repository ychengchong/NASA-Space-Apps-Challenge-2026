import { describe, expect, test } from "vitest";
import {
  formatCoordinates,
  formatNumber,
  formatPValue,
  formatRate,
  formatRatePerDecade,
  formatSignedRate,
  splitSign,
  withUnits,
} from "./format";

describe("formatRate", () => {
  test("rounds to the variable's decimals", () => {
    expect(formatRate(0.2349, 2)).toBe("0.23");
  });

  test("shows the size of a falling rate without a sign", () => {
    expect(formatRate(-0.31, 2)).toBe("0.31");
  });

  test("shows one more digit when the rate rounds to zero", () => {
    expect(formatRate(0.004, 2)).toBe("0.004");
  });

  test("shows only one more digit when that still rounds to zero", () => {
    expect(formatRate(0.0004, 2)).toBe("0.000");
  });

  test("keeps the variable's decimals when the rate does not round to zero", () => {
    expect(formatRate(0.006, 2)).toBe("0.01");
  });

  test("rounds an exact tie to the even digit, as Python does", () => {
    expect(formatRate(0.125, 2)).toBe("0.12");
    expect(formatRate(0.375, 2)).toBe("0.38");
  });

  test("rounds an exact tie to a whole number to the even number", () => {
    expect(formatRate(2.5, 0)).toBe("2");
    expect(formatRate(3.5, 0)).toBe("4");
  });
});

describe("splitSign", () => {
  test("parts the sign of a rising rate from its digits", () => {
    expect(splitSign("+0.79")).toEqual(["+", "0.79"]);
  });

  test("parts the sign of a falling rate from its digits", () => {
    expect(splitSign("-1.3")).toEqual(["-", "1.3"]);
  });

  test("gives a rate without a sign an empty sign and all its digits", () => {
    expect(splitSign("0.000")).toEqual(["", "0.000"]);
  });
});

describe("formatSignedRate", () => {
  test("puts a plus sign before a rising rate", () => {
    expect(formatSignedRate(0.31, 2)).toBe("+0.31");
  });

  test("puts a minus sign before a falling rate", () => {
    expect(formatSignedRate(-0.31, 2)).toBe("-0.31");
  });

  test("keeps the sign when the extra digit is shown", () => {
    expect(formatSignedRate(-0.004, 2)).toBe("-0.004");
  });

  test("gives a zero rate no sign", () => {
    expect(formatSignedRate(0, 2)).toBe("0.000");
  });

  test("rounds a negative exact tie to the even digit", () => {
    expect(formatSignedRate(-0.125, 2)).toBe("-0.12");
  });
});

describe("formatPValue", () => {
  test("shows three decimals", () => {
    expect(formatPValue(0.0633)).toBe("0.063");
  });

  test("keeps trailing zeros", () => {
    expect(formatPValue(0.05)).toBe("0.050");
  });

  test("shows a p-value below 0.001 as less than 0.001", () => {
    expect(formatPValue(0.00068)).toBe("< 0.001");
  });

  test("shows a p-value of exactly 0.001 as a number", () => {
    expect(formatPValue(0.001)).toBe("0.001");
  });

  test("shows a p-value of one", () => {
    expect(formatPValue(1)).toBe("1.000");
  });
});

describe("formatCoordinates", () => {
  test("writes north and east with one decimal", () => {
    expect(formatCoordinates(60, 25)).toBe("60.0°N, 25.0°E");
  });

  test("writes south and west for negative values", () => {
    expect(formatCoordinates(-1.29, -36.82)).toBe("1.3°S, 36.8°W");
  });

  test("writes the equator and the prime meridian as north and east", () => {
    expect(formatCoordinates(0, 0)).toBe("0.0°N, 0.0°E");
  });

  test("rounds a grid point on an exact tie to the even digit, as Python does", () => {
    expect(formatCoordinates(55.5, 21.25)).toBe("55.5°N, 21.2°E");
  });
});

describe("formatNumber", () => {
  test("rounds to the given decimals and keeps the sign", () => {
    expect(formatNumber(-2.614, 2)).toBe("-2.61");
  });

  test("rounds an exact tie to the even digit, as Python does", () => {
    expect(formatNumber(-0.125, 2)).toBe("-0.12");
  });
});

describe("withUnits", () => {
  test("puts the units after the number", () => {
    expect(withUnits("0.25", "°C")).toBe("0.25 °C");
  });

  test("writes the number alone for a variable without units", () => {
    expect(withUnits("0.004", "")).toBe("0.004");
  });
});

describe("formatRatePerDecade", () => {
  test("writes a signed rate with the rate units before per decade", () => {
    expect(formatRatePerDecade(0.4849, { decimals: 2, rate_units: "°C" })).toBe("+0.48 °C per decade");
  });

  test("writes a falling rate with a minus sign", () => {
    expect(formatRatePerDecade(-1.26, { decimals: 1, rate_units: "percentage points" })).toBe(
      "-1.3 percentage points per decade",
    );
  });

  test("leaves out the units for a variable without them", () => {
    expect(formatRatePerDecade(0.004, { decimals: 2, rate_units: "" })).toBe("+0.004 per decade");
  });
});
