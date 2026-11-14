import type { Layout, ScatterTrace } from "plotly.js-basic-dist-min";
import { lazy, Suspense, useMemo } from "react";
import type { JSX } from "react";
import type { Gap, Investigation, VariableSummary } from "../api";
import { AXIS_LINE, AXIS_STYLE, BASE_LAYOUT, HOVER_TEXT_ONLY, plotlyText } from "../chartStyle";
import { formatNumber, withUnits } from "../format";

const PlotlyChart = lazy(() => import("./PlotlyChart"));

const CHART_HEIGHT_PX = 260;
const GAP_COLOUR = "#4a3d30";

/**
 * The gap between the two places of a comparison (spec 7, "The gap between two places"): the
 * API's yearly differences and their trend line against a zero line, with the API's sentence.
 */
export function GapChart({ investigation }: { investigation: Investigation }): JSX.Element | null {
  const { gap, variable } = investigation;
  const data = useMemo(() => (gap ? gapTraces(gap, variable) : []), [gap, variable]);
  const layout = useMemo(() => gapLayout(variable), [variable]);
  if (!gap || gap.same_cell || gap.series.length === 0) return null;
  return (
    <section className="panel" aria-labelledby="gap-heading">
      <h2 id="gap-heading">
        The gap: {gap.first_place} minus {gap.second_place}
      </h2>
      <Suspense fallback={<div className="chart-placeholder">Loading the chart…</div>}>
        <PlotlyChart data={data} layout={layout} description={gap.sentence} />
      </Suspense>
      <p className="panel-intro">
        Each point is {gap.first_place}&apos;s yearly value minus {gap.second_place}&apos;s, in a year both
        places have. Above zero, {gap.first_place} was higher.
      </p>
      <p className="chart-summary">{gap.sentence}</p>
    </section>
  );
}

function gapTraces(gap: Gap, variable: VariableSummary): ScatterTrace[] {
  const name = `${plotlyText(gap.first_place)} minus ${plotlyText(gap.second_place)}`;
  const traces: ScatterTrace[] = [
    {
      type: "scatter",
      mode: "lines+markers",
      name,
      x: gap.series.map((point) => point.year),
      y: gap.series.map((point) => point.value),
      text: gap.series.map((point) =>
        point.value === null
          ? `${name}<br>${point.year}: no value`
          : `${name}<br>${point.year}: ${withUnits(formatNumber(point.value, variable.decimals), variable.units)}`,
      ),
      hovertemplate: HOVER_TEXT_ONLY,
      line: { color: GAP_COLOUR, width: 1.5 },
      marker: { color: GAP_COLOUR, size: 6 },
    },
  ];
  const { line, first_year: firstYear, last_year: lastYear } = gap;
  if (line !== null && firstYear !== null && lastYear !== null) {
    const ends: [number, number][] = [
      [firstYear, line[0]],
      [lastYear, line[1]],
    ];
    traces.push({
      type: "scatter",
      mode: "lines",
      name: "Trend line of the gap",
      x: ends.map(([year]) => year),
      y: ends.map(([, value]) => value),
      text: ends.map(
        ([year, value]) =>
          `Trend line in ${year}: ${withUnits(formatNumber(value, variable.decimals), variable.units)}`,
      ),
      hovertemplate: HOVER_TEXT_ONLY,
      line: { color: GAP_COLOUR, width: 2.5, dash: "dash" },
    });
  }
  return traces;
}

function gapLayout(variable: VariableSummary): Layout {
  return {
    ...BASE_LAYOUT,
    height: CHART_HEIGHT_PX,
    xaxis: { ...AXIS_STYLE, type: "linear", tickformat: "d", title: { text: "Year" } },
    yaxis: {
      ...AXIS_STYLE,
      zeroline: true,
      zerolinecolor: AXIS_LINE,
      title: { text: `Difference (${variable.units})` },
    },
  };
}
