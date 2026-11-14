/**
 * One colour and one marker shape per place, shared by the chart, the globe and the place lists,
 * so a place is never told apart by colour alone (spec 3).
 */

export type MarkerShape = "circle" | "square" | "triangle" | "diamond";

export interface PlaceStyle {
  color: string;
  shape: MarkerShape;
  /** The matching Plotly marker symbol. */
  plotlySymbol: "circle" | "square" | "triangle-up" | "diamond";
}

// Four hues of the dataviz reference palette, teal, ochre, violet and magenta, chosen with its
// validator for the paper sheet the charts lie on (#f7f0de). Teal and ochre are the palette's
// aqua and yellow, darkened at the same hue until they reach 3:1 on the sheet; violet and
// magenta are documented steps. Every ink has 3:1 contrast or more on the sheet. The order
// passes every check of the validator between neighbours, as lines on a chart need, and between
// all pairs for the first three. The first and the fourth, teal and magenta, are close under
// red-green colour blindness, so a case of four places leans on the marker shapes and the names.
// The first two inks keep clear of the red and the blue that mean rising and falling (spec 3).
const PLACE_STYLES: readonly PlaceStyle[] = [
  { color: "#039b6a", shape: "circle", plotlySymbol: "circle" },
  { color: "#b57a00", shape: "square", plotlySymbol: "square" },
  { color: "#6250d6", shape: "triangle", plotlySymbol: "triangle-up" },
  { color: "#d55181", shape: "diamond", plotlySymbol: "diamond" },
];

/** The style of the place at `index` in the case; a case holds four places at most. */
export function placeStyle(index: number): PlaceStyle {
  const style = PLACE_STYLES[index % PLACE_STYLES.length];
  if (style === undefined) throw new RangeError(`No place style for index ${index}.`);
  return style;
}
