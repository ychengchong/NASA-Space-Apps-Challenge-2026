/**
 * How the screen names a season. Spec 3, "Wording and accessibility": seasons are named by their
 * months, because "winter" means different months in each hemisphere.
 */

import type { Season } from "./api";

export const SEASON_LABELS: Readonly<Record<Season, string>> = {
  annual: "Every month",
  DJF: "December to February",
  MAM: "March to May",
  JJA: "June to August",
  SON: "September to November",
};

/** The seasons in the order the season picker lists them. */
export const SEASON_ORDER: readonly Season[] = ["annual", "DJF", "MAM", "JJA", "SON"];

export function seasonLabel(season: Season): string {
  return SEASON_LABELS[season];
}

/** What one yearly value averages, as it reads inside a sentence. */
export function seasonAverageText(season: Season): string {
  return season === "annual" ? "the average of all twelve months" : `the average of ${SEASON_LABELS[season]}`;
}

export function isSeason(value: string): value is Season {
  return Object.hasOwn(SEASON_LABELS, value);
}
