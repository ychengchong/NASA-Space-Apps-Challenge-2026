/**
 * The diverging colour scale of the region view (spec 7, "Region view"): every cell with a result
 * is coloured by its rate, with a neutral grey at zero, so the sign reads at a glance.
 *
 * The colours are the dataviz reference palette's diverging pair: its blue ramp for a falling
 * rate and a red arm stepped to the same OKLCH lightness, around its neutral grey. Blue against
 * red stays apart under the common forms of colour blindness, and each arm darkens steadily
 * with the size of the rate.
 */

export const NEUTRAL_COLOUR = "#f0efec";
// From the neutral end outward.
const FALLING_ARM: readonly string[] = ["#9ec5f4", "#5598e7", "#256abf", "#104281"];
const RISING_ARM: readonly string[] = ["#f1aea8", "#dd716a", "#b13f3c", "#762221"];

// "Nice" leading digits for the end of the scale, so the legend reads 0.8 rather than 0.734.
const NICE_STEPS: readonly number[] = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
// Significant digits kept while finding the scale's end, which drops float noise such as
// 0.8000000000000002 or 5.999999999999999.
const LIMIT_PRECISION = 12;
// More decimals than a scale end of LIMIT_PRECISION significant digits can need.
const MAX_LIMIT_DECIMALS = 20;

/**
 * The colour of a rate per decade on a scale that runs from -limit to +limit. Zero is the neutral
 * grey, a rise takes the red arm and a fall the blue arm, and a rate beyond the scale takes the
 * colour of its end. A limit of zero or less colours everything neutral.
 */
export function slopeColour(slope: number, limit: number): string {
  if (!(limit > 0) || slope === 0) return NEUTRAL_COLOUR;
  const position = Math.min(Math.abs(slope) / limit, 1);
  const stops = [NEUTRAL_COLOUR, ...(slope > 0 ? RISING_ARM : FALLING_ARM)];
  const scaled = position * (stops.length - 1);
  const lower = Math.min(Math.floor(scaled), stops.length - 2);
  return mixHex(stop(stops, lower), stop(stops, lower + 1), scaled - lower);
}

/**
 * The end of the scale: the largest rate's size rounded up to a nice number, or 0 when no rate
 * is given or every rate is zero. Missing rates are skipped.
 */
export function scaleLimit(slopes: readonly (number | null)[]): number {
  const largest = Math.max(0, ...slopes.map((slope) => (slope === null ? 0 : Math.abs(slope))));
  if (largest === 0 || !Number.isFinite(largest)) return 0;
  const magnitude = 10 ** Math.floor(Math.log10(largest));
  const leading = Number((largest / magnitude).toPrecision(LIMIT_PRECISION));
  const nice = NICE_STEPS.find((step) => step >= leading) ?? 10;
  return Number((nice * magnitude).toPrecision(LIMIT_PRECISION));
}

/**
 * The decimals for writing the end of the scale in the legend: enough to write `limit` exactly,
 * such as 0.15 rather than 0.1, so the legend names the rate where the colours stop, and never
 * fewer than the variable's own `decimals`.
 */
export function scaleEndDecimals(limit: number, decimals: number): number {
  for (let exact = 0; exact < MAX_LIMIT_DECIMALS; exact++) {
    if (Number(limit.toFixed(exact)) === limit) return Math.max(decimals, exact);
  }
  return Math.max(decimals, MAX_LIMIT_DECIMALS);
}

/** A CSS gradient of the whole scale from -limit on the left to +limit on the right. */
export function scaleGradient(): string {
  const colours = [...FALLING_ARM].reverse().concat(NEUTRAL_COLOUR, RISING_ARM);
  return `linear-gradient(to right, ${colours.join(", ")})`;
}

function stop(stops: readonly string[], index: number): string {
  const colour = stops[index];
  if (colour === undefined) throw new RangeError(`No colour stop at ${index}.`);
  return colour;
}

function mixHex(from: string, to: string, share: number): string {
  const start = channels(from);
  const end = channels(to);
  const mixed = start.map((value, index) => Math.round(value + ((end[index] ?? value) - value) * share));
  return `#${mixed.map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function channels(hex: string): number[] {
  return [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
}
