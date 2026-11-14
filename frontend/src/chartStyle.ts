/** Layout settings shared by the app's Plotly charts, matching the paper sheets they lie on. */

import type { Layout } from "plotly.js-basic-dist-min";

const INK = "#2a2018";
const GRID = "rgba(42, 32, 24, 0.13)";
// The page's text face (styles.css, --font).
const FONT_FAMILY = '"Libre Baskerville", Baskerville, Georgia, "Times New Roman", serif';
// A chart has no ground of its own, so the sheet it lies on shows through.
const NO_FILL = "rgba(0, 0, 0, 0)";

/** The colour of axis lines and of reference lines drawn across a chart. */
export const AXIS_LINE = "#4a3d30";
/** The colour of the sheets, for the ring that sets a marker off from the line through it. */
export const SURFACE = "#f7f0de";

export const BASE_LAYOUT: Layout = {
  margin: { l: 8, r: 8, t: 8, b: 8 },
  paper_bgcolor: NO_FILL,
  plot_bgcolor: NO_FILL,
  font: { family: FONT_FAMILY, size: 13, color: INK },
  hovermode: "closest",
  // Above the plot, so a legend of several rows never covers the axis title.
  legend: { orientation: "h", x: 0, y: 1.02, yanchor: "bottom" },
};

export const AXIS_STYLE = {
  gridcolor: GRID,
  linecolor: AXIS_LINE,
  zeroline: false,
  automargin: true,
  fixedrange: true,
} as const;

/**
 * Text for a Plotly label or hover text. Plotly reads tags such as <a> and <b> in these strings,
 * so user text, like a place label, is escaped to stay plain text (AGENTS.md, section 7).
 */
export function plotlyText(text: string): string {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

/** Hover text shows the trace's prepared `text` only. */
export const HOVER_TEXT_ONLY = "%{text}<extra></extra>";
