/** How the seasons panel writes a row's years and its significance (spec 7, "All seasons at once"). */

import type { SeasonRate, SeasonRates, Verdict } from "./api";

const ASSESSED_LABELS: Readonly<Partial<Record<Verdict["kind"], string>>> = {
  significant: "Significant, from the trend test",
  not_significant: "Not significant, from the trend test",
};

/** The years a row used, such as "1982 to 2025 (44)", or "None" when it used none. */
export function yearsText(rate: SeasonRate): string {
  if (rate.first_year === null || rate.last_year === null) return "None";
  return `${rate.first_year} to ${rate.last_year} (${rate.n})`;
}

/**
 * Only a row the API marks as assessed, which the inference gate allows for annual air
 * temperature alone, names a test's verdict; every other row with a rate says it was not assessed.
 */
export function significanceText(rate: SeasonRate): string {
  if (rate.assessed) return ASSESSED_LABELS[rate.verdict_kind] ?? "Not assessed";
  if (rate.verdict_kind === "too_few_years") return "Too few years";
  if (rate.verdict_kind === "no_data") return "No data";
  return "Not assessed";
}

/**
 * The seasons chart's text for screen readers: each place's name, then its rows' sentences as the
 * API wrote them, so the places of a comparison can be told apart.
 */
export function chartDescription(answer: SeasonRates): string {
  return answer.places
    .map((place) => `${place.place.name}: ${place.rates.map((rate) => rate.sentence).join(" ")}`)
    .join(" ");
}
