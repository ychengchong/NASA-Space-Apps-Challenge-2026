/**
 * How the screen names a season. Spec 3, "Wording and accessibility": seasons are named by their
 * months, because "winter" means different months in each hemisphere.
 */

import type { Requested, Season } from "./api";

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

/** The months a season covers, as they read after a period: "all months" or "June to August". */
export function seasonMonthsText(season: Season): string {
  return season === "annual" ? "all months" : SEASON_LABELS[season];
}

/** The years and months a case or a map tests, such as "1981 to 2025, all months". */
export function periodText(requested: Requested): string {
  return `${requested.from} to ${requested.to}, ${seasonMonthsText(requested.season)}`;
}

/** What one yearly value averages, as it reads inside a sentence. */
export function seasonAverageText(season: Season): string {
  return season === "annual" ? "the average of all twelve months" : `the average of ${SEASON_LABELS[season]}`;
}

export function isSeason(value: string): value is Season {
  return Object.hasOwn(SEASON_LABELS, value);
}
