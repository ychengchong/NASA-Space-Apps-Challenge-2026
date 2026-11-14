/** Helpers for the period explorer, which draws the scan of spec 7, step 10. */

import type { ScanPoint } from "./api";
import type { CaseParams } from "./caseUrl";

// Spec 7, step 6: a trend is significant when p is below 0.05. The scan uses the same test.
export const SIGNIFICANCE_LEVEL = 0.05;

/**
 * True when a scan point would get the "significant" verdict. Spec 7, verdict rules: a Sen's
 * slope of exactly zero is not significant, whatever p is, so the explorer agrees with the case.
 */
export function isSignificant(point: ScanPoint): boolean {
  return point.sen_slope !== 0 && point.mk_p < SIGNIFICANCE_LEVEL;
}

/** Years written as runs: [1981, 1982, 1983, 1990] -> "1981 to 1983 and 1990". */
export function yearRuns(years: readonly number[]): string {
  const runs: [number, number][] = [];
  for (const year of [...years].sort((a, b) => a - b)) {
    const last = runs.at(-1);
    if (last !== undefined && year === last[1] + 1) last[1] = year;
    else runs.push([year, year]);
  }
  const texts = runs.map(([first, last]) => (first === last ? String(first) : `${first} to ${last}`));
  if (texts.length <= 1) return texts[0] ?? "";
  return `${texts.slice(0, -1).join(", ")} and ${texts.at(-1) ?? ""}`;
}

/**
 * The case that choosing `year` as the first year opens: the same case from that year. The page
 * then asks /api/case again, which alone gives the verdict (spec 10).
 */
export function caseFromFirstYear(params: CaseParams, year: number): CaseParams {
  return { ...params, from: year };
}
