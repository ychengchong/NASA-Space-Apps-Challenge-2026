/** Layout settings shared by the app's Plotly charts, matching the page's light theme. */

import type { Layout } from "plotly.js-basic-dist-min";

const INK = "#1d232b";
const GRID = "#e3e6ea";
const AXIS_LINE = "#9aa3ad";
const FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

export const BASE_LAYOUT: Layout = {
  margin: { l: 8, r: 8, t: 8, b: 8 },
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#ffffff",
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
