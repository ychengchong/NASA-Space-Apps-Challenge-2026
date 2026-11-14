/** How a place's overview is laid out (spec 7, "What is changing here?"). */

import type { OverviewRow, PlaceOverview } from "./api";
import { casePageUrl } from "./route";

export interface ThemeRows {
  theme: string;
  rows: OverviewRow[];
}

/**
 * The rows grouped by theme, themes in the order they first appear and rows in the API's order
 * within each. Nothing is sorted by rate: rates in different units cannot be compared.
 */
export function overviewThemes(rows: readonly OverviewRow[]): ThemeRows[] {
  const groups = new Map<string, OverviewRow[]>();
  for (const row of rows) {
    const group = groups.get(row.variable.theme);
    if (group === undefined) groups.set(row.variable.theme, [row]);
    else group.push(row);
  }
  return [...groups].map(([theme, grouped]) => ({ theme, rows: grouped }));
}

/** The ordinary case of one row: its variable at the place, over its own record in the period. */
export function rowCaseUrl(row: OverviewRow, overview: PlaceOverview): string {
  return casePageUrl({
    variable: row.variable.id,
    places: [{ lat: overview.lat, lon: overview.lon, name: overview.name }],
    from: Math.max(overview.requested.from, row.variable.record_start),
    to: overview.requested.to,
    season: overview.requested.season,
  });
}
