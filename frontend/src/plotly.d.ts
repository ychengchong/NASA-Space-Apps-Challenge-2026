/**
 * The part of plotly.js-basic-dist-min that this app uses. That bundle holds only the bar, pie
 * and scatter traces, so every chart here is drawn with scatter traces. The package ships no
 * types, and the project adds no type package for it.
 */
declare module "plotly.js-basic-dist-min" {
  export type Datum = string | number | null;

  export interface ScatterTrace {
    type: "scatter";
    mode: "lines" | "markers" | "lines+markers";
    name: string;
    x: Datum[];
    y: Datum[];
    text?: string[];
    hovertemplate?: string;
    connectgaps?: boolean;
    showlegend?: boolean;
    legendgroup?: string;
    opacity?: number;
    line?: { color?: string; width?: number; dash?: "solid" | "dash" | "dot" };
    marker?: {
      color?: string;
      size?: number;
      symbol?: string | string[];
      line?: { color?: string; width?: number };
    };
  }

  export interface Axis {
    title?: { text: string };
    type?: "date" | "linear" | "category";
    gridcolor?: string;
    linecolor?: string;
    zeroline?: boolean;
    zerolinecolor?: string;
    automargin?: boolean;
    fixedrange?: boolean;
    tickformat?: string;
    rangemode?: "normal" | "tozero";
  }

  export interface Shape {
    type: "line";
    xref: "x";
    yref: "paper";
    x0: Datum;
    x1: Datum;
    y0: number;
    y1: number;
    line: { color: string; width: number; dash?: "solid" | "dash" | "dot" };
  }

  export interface Layout {
    height?: number;
    margin?: { l?: number; r?: number; t?: number; b?: number };
    xaxis?: Axis;
    yaxis?: Axis;
    legend?: { orientation?: "h" | "v"; x?: number; y?: number; yanchor?: "top" | "bottom" };
    hovermode?: "closest" | "x" | "x unified" | false;
    paper_bgcolor?: string;
    plot_bgcolor?: string;
    font?: { family?: string; size?: number; color?: string };
    shapes?: Shape[];
    showlegend?: boolean;
  }

  export interface Config {
    responsive?: boolean;
    displayModeBar?: boolean;
  }

  export interface ClickPoint {
    x: Datum;
    y: Datum;
    curveNumber: number;
    pointIndex: number;
  }

  export interface PlotlyElement extends HTMLDivElement {
    on(event: "plotly_click", handler: (event: { points: ClickPoint[] }) => void): void;
    removeAllListeners(event: "plotly_click"): void;
  }

  interface PlotlyStatic {
    react(root: HTMLElement, data: ScatterTrace[], layout: Layout, config?: Config): Promise<PlotlyElement>;
    purge(root: HTMLElement): void;
  }

  const Plotly: PlotlyStatic;
  export default Plotly;
}
