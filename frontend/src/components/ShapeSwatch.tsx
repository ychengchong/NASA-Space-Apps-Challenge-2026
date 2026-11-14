import type { CSSProperties, JSX } from "react";
import { placeStyle } from "../placeStyles";

/** The colour and marker shape of the place at `index`, as drawn on the chart and the map. */
export function ShapeSwatch({ index }: { index: number }): JSX.Element {
  const style = placeStyle(index);
  const colour = { "--place-color": style.color } as CSSProperties;
  return <span className={`shape-swatch shape-${style.shape}`} style={colour} aria-hidden="true" />;
}
