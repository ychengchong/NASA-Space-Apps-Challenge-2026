/**
 * Display formatting for numbers the backend computed. Nothing here computes a statistic.
 *
 * Rounding matches Python's format(value, ".Nf"), so the screen shows the same digits as the
 * verdict sentences the backend writes.
 */

// A p-value below this is shown as "< 0.001", never rounded to zero.
const P_VALUE_FLOOR = 0.001;
const P_VALUE_DECIMALS = 3;
// Spec 5 and 7: a grid point reads like "60.0°N, 25.0°E".
const COORDINATE_DECIMALS = 1;
// Number.prototype.toFixed accepts at most 100 digits, enough to write any value shown here exactly.
const EXACT_DIGITS = 100;

/**
 * The size of a rate per decade, without a sign, as in the verdict sentence's "{rate}".
 * Spec 7: if rounding to `decimals` gives zero, one more digit is shown.
 */
export function formatRate(perDecade: number, decimals: number): string {
  const size = Math.abs(perDecade);
  const text = toFixed(size, decimals);
  return Number(text) === 0 ? toFixed(size, decimals + 1) : text;
}

/** A rate per decade with "+" or "-" in front, as in "{signed rate}"; zero has no sign. */
export function formatSignedRate(perDecade: number, decimals: number): string {
  const size = formatRate(perDecade, decimals);
  if (perDecade > 0) return `+${size}`;
  if (perDecade < 0) return `-${size}`;
  return size;
}

/**
 * A signed rate as its sign and its digits, so the two can be set in different type: ["+", "0.79"]
 * for "+0.79", and ["", "0.00"] for a rate without a sign. Nothing is added or taken away.
 */
export function splitSign(signedRate: string): [sign: string, digits: string] {
  const sign = signedRate.charAt(0);
  return sign === "+" || sign === "-" ? [sign, signedRate.slice(1)] : ["", signedRate];
}

/** A p-value with three decimals, or "< 0.001" when it is smaller than that. */
export function formatPValue(p: number): string {
  if (p < P_VALUE_FLOOR) return `< ${toFixed(P_VALUE_FLOOR, P_VALUE_DECIMALS)}`;
  return toFixed(p, P_VALUE_DECIMALS);
}

/** A value rounded to `decimals` digits, written as Python's format(value, ".Nf") writes it. */
export function formatNumber(value: number, decimals: number): string {
  return toFixed(value, decimals);
}

/** A signed rate with the variable's rate units, such as "+0.48 °C per decade". */
export function formatRatePerDecade(
  perDecade: number,
  variable: { decimals: number; rate_units: string },
): string {
  return `${withUnits(formatSignedRate(perDecade, variable.decimals), variable.rate_units)} per decade`;
}

/** A formatted number followed by its units, or the number alone for a variable without units. */
export function withUnits(text: string, units: string): string {
  return units === "" ? text : `${text} ${units}`;
}

/** Coordinates such as "60.0°N, 25.0°E". */
export function formatCoordinates(lat: number, lon: number): string {
  const latitude = `${toFixed(Math.abs(lat), COORDINATE_DECIMALS)}°${lat < 0 ? "S" : "N"}`;
  const longitude = `${toFixed(Math.abs(lon), COORDINATE_DECIMALS)}°${lon < 0 ? "W" : "E"}`;
  return `${latitude}, ${longitude}`;
}

/**
 * Like Number.prototype.toFixed, but an exact tie rounds to the even digit as Python does,
 * where toFixed rounds it away from zero. Example: 0.125 to two decimals is "0.12", not "0.13".
 */
function toFixed(value: number, decimals: number): string {
  const rounded = value.toFixed(decimals);
  const exact = Math.abs(value).toFixed(EXACT_DIGITS);
  const point = exact.indexOf(".");
  const droppedDigits = exact.slice(point + 1 + decimals);
  const isTie = /^50*$/.test(droppedDigits);
  if (!isTie) return rounded;

  const keptDigits = exact.slice(0, decimals === 0 ? point : point + 1 + decimals);
  const isLastDigitEven = Number(keptDigits.at(-1)) % 2 === 0;
  if (!isLastDigitEven) return rounded;
  return value < 0 ? `-${keptDigits}` : keptDigits;
}
