/**
 * One colour and one marker shape per place, shared by the chart, the map and the place lists, so
 * a place is never told apart by colour alone (spec 3).
 */

export type MarkerShape = "circle" | "square" | "triangle" | "diamond";

export interface PlaceStyle {
  color: string;
  shape: MarkerShape;
  /** The matching Plotly marker symbol. */
  plotlySymbol: "circle" | "square" | "triangle-up" | "diamond";
}

// The first four categorical slots of the dataviz reference palette, in their fixed order. Some
// sit below 3:1 contrast on white, so every chart also has a legend, shapes and a table view.
const PLACE_STYLES: readonly PlaceStyle[] = [
  { color: "#2a78d6", shape: "circle", plotlySymbol: "circle" },
  { color: "#eb6834", shape: "square", plotlySymbol: "square" },
  { color: "#1baf7a", shape: "triangle", plotlySymbol: "triangle-up" },
  { color: "#eda100", shape: "diamond", plotlySymbol: "diamond" },
];

/** The style of the place at `index` in the case; a case holds four places at most. */
export function placeStyle(index: number): PlaceStyle {
  const style = PLACE_STYLES[index % PLACE_STYLES.length];
  if (style === undefined) throw new RangeError(`No place style for index ${index}.`);
  return style;
}
