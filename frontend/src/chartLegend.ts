/**
 * The trend chart's legend (spec 3, "Chart"). It must fit one row above the plot, so one place
 * names its kinds of mark without repeating the place, and a comparison names only its places:
 * their monthly values, record rings and trend lines share each place's ink and are told apart in
 * the line under the plot.
 */

export type ChartMark = "monthly values" | "yearly values" | "record years" | "trend line";

export interface LegendEntry {
  /** The trace's name, for the legend and for the hover text's grouping. */
  name: string;
  showlegend: boolean;
}

export function legendEntry(placeName: string, mark: ChartMark, placeCount: number): LegendEntry {
  if (placeCount <= 1) return { name: mark.charAt(0).toUpperCase() + mark.slice(1), showlegend: true };
  if (mark === "yearly values") return { name: placeName, showlegend: true };
  return { name: `${placeName}: ${mark}`, showlegend: false };
}
