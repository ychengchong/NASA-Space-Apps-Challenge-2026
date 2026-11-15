import Plotly from "plotly.js-basic-dist-min";
import type { ClickPoint, Config, Layout, ScatterTrace } from "plotly.js-basic-dist-min";
import { useEffect, useEffectEvent, useRef } from "react";
import type { JSX } from "react";

// The axes do not zoom and the values are in a table, so the chart needs no toolbar.
const CONFIG: Config = { responsive: true, displayModeBar: false };
// The class Plotly gives an element once it has drawn a chart in it.
const PLOTTED_CLASS = "js-plotly-plot";

interface PlotlyChartProps {
  data: ScatterTrace[];
  layout: Layout;
  /** A plain-text description for screen readers, which cannot read the drawing. */
  description: string;
  onPointClick?: (point: ClickPoint) => void;
}

/**
 * A Plotly chart. This module carries the large Plotly bundle, so callers load it with
 * React.lazy to keep the first paint fast. `data` and `layout` should keep their identity
 * between renders unless they change, because each change redraws the chart.
 */
export default function PlotlyChart({
  data,
  layout,
  description,
  onPointClick,
}: PlotlyChartProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const handleClick = useEffectEvent((point: ClickPoint) => onPointClick?.(point));

  useEffect(() => {
    const container = containerRef.current;
    if (container === null) return;
    let cancelled = false;
    void Plotly.react(container, data, layout, CONFIG).then((plot) => {
      if (cancelled) return;
      plot.removeAllListeners("plotly_click");
      plot.on("plotly_click", (event) => {
        const point = event.points[0];
        if (point !== undefined) handleClick(point);
      });
    });
    return () => {
      cancelled = true;
    };
  }, [data, layout]);

  useEffect(() => {
    const container = containerRef.current;
    return () => {
      if (container !== null) Plotly.purge(container);
    };
  }, []);

  // Plotly follows only the window's size. A chart drawn in a hidden tab of the case file has no
  // width of its own, so it is redrawn to its box once the tab shows it (spec 3, "Case file tabs").
  useEffect(() => {
    const container = containerRef.current;
    if (container === null || typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(() => {
      if (container.offsetWidth > 0 && container.classList.contains(PLOTTED_CLASS)) {
        void Plotly.Plots.resize(container);
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  return <div className="plotly-chart" ref={containerRef} role="img" aria-label={description} />;
}
