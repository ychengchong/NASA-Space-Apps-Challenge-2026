/** The words shown beside a region map's cell while the pointer is on it (spec 7, "Region view"). */

import type { MapCell, VariableSummary } from "./api";
import { formatCoordinates, formatPValue, formatRatePerDecade } from "./format";

/**
 * The lines of a cell's tooltip: its grid point, then its rate per decade and p-value, or the
 * reason it has neither, then what a click does. The numbers are the API's, formatted only.
 */
export function cellTooltipLines(cell: MapCell, variable: VariableSummary): string[] {
  const lines = [formatCoordinates(cell.lat, cell.lon)];
  if (cell.sen_slope === null || cell.mk_p === null) {
    lines.push("No result: too few complete years to test.");
  } else {
    lines.push(formatRatePerDecade(cell.sen_slope, variable), pValueText(cell.mk_p));
    if (cell.significant) lines.push("Marked: passes the map's stricter test.");
  }
  lines.push("Click to open this cell as a case.");
  return lines;
}

/** "p = 0.012", or "p < 0.001" for a p-value below what is printed. */
function pValueText(p: number): string {
  const text = formatPValue(p);
  return text.startsWith("<") ? `p ${text}` : `p = ${text}`;
}
