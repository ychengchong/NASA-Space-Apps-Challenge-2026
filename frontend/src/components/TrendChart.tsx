import type { Layout, ScatterTrace } from "plotly.js-basic-dist-min";
import { lazy, Suspense, useMemo, useState } from "react";
import type { JSX } from "react";
import { getSeries } from "../api";
import type { Investigation, PlaceResult, Season, Series, VariableSummary } from "../api";
import { joinWords } from "../cautions";
import { AXIS_STYLE, BASE_LAYOUT, HOVER_TEXT_ONLY, plotlyText, SURFACE } from "../chartStyle";
import { formatNumber, formatRatePerDecade, formatSignedRate, withUnits } from "../format";
import { placeStyle } from "../placeStyles";
import { seasonAverageText } from "../seasons";
import { useRequest } from "../useRequest";
import { ShapeSwatch } from "./ShapeSwatch";

const PlotlyChart = lazy(() => import("./PlotlyChart"));

const CHART_HEIGHT_PX = 380;

// Each yearly point sits in the middle of the months it averages, so it lines up with the
// monthly values; December to February centres on January of its year (spec 7, step 2).
const SEASON_CENTRE: Readonly<Record<Season, string>> = {
  annual: "07-01",
  DJF: "01-15",
  MAM: "04-15",
  JJA: "07-15",
  SON: "10-15",
};
const MID_MONTH_DAY = "15";

interface TrendChartProps {
  investigation: Investigation;
}

/** The yearly values and the trend line of each place, with the monthly values on request. */
export function TrendChart({ investigation }: TrendChartProps): JSX.Element {
  const [showMonthly, setShowMonthly] = useState(false);
  const monthly = useRequest(showMonthly ? `monthly:${investigation.id}` : null, (signal) =>
    loadMonthly(investigation, signal),
  );
  const monthlySeries = monthly.state.status === "done" ? monthly.state.value : null;

  const data = useMemo(() => chartTraces(investigation, monthlySeries), [investigation, monthlySeries]);
  const layout = useMemo(() => chartLayout(investigation.variable), [investigation.variable]);
  const summary = chartSummary(investigation);

  return (
    <section className="panel sheet" aria-labelledby="chart-heading">
      <div className="panel-heading-row">
        <h2 id="chart-heading">Yearly values and trend</h2>
        <button
          type="button"
          className="button button-secondary"
          aria-pressed={showMonthly}
          onClick={() => setShowMonthly((shown) => !shown)}
        >
          {showMonthly ? "Hide monthly values" : "Show monthly values"}
        </button>
      </div>
      <p className="status-text" role="status">
        {monthly.state.status === "loading" ? "Loading the monthly values…" : null}
        {monthly.state.status === "failed"
          ? `The monthly values could not be loaded. ${monthly.state.error.message}`
          : null}
      </p>
      <Suspense fallback={<div className="chart-placeholder">Loading the chart…</div>}>
        <PlotlyChart data={data} layout={layout} description={summary.join(" ")} />
      </Suspense>
      <p className="panel-intro">
        Each point is {seasonAverageText(investigation.requested.season)} in one year, from{" "}
        {investigation.requested.from} to {investigation.requested.to}. A gap means a year with a missing
        month.
      </p>
      <ul className="chart-summary">
        {investigation.results.map((result, index) => (
          <li key={index}>
            <ShapeSwatch index={index} /> {placeSummary(result, investigation.variable)}
          </li>
        ))}
      </ul>
      <details className="disclosure">
        <summary>Show the yearly values as a table</summary>
        <YearlyTable investigation={investigation} />
      </details>
    </section>
  );
}

function loadMonthly(investigation: Investigation, signal: AbortSignal): Promise<Series[]> {
  const { variable, requested, results } = investigation;
  return Promise.all(
    results.map((result) =>
      getSeries(
        {
          variable: variable.id,
          place: { lat: result.place.lat, lon: result.place.lon },
          from: requested.from,
          to: requested.to,
          season: requested.season,
          resolution: "monthly",
          snapshotIds: result.snapshot_id ? [result.snapshot_id] : undefined,
          analysisVersion: investigation.analysis_version,
        },
        signal,
      ),
    ),
  );
}

function yearDate(year: number, season: Season): string {
  return `${year}-${SEASON_CENTRE[season]}`;
}

function valueText(value: number, variable: VariableSummary): string {
  return withUnits(formatNumber(value, variable.decimals), variable.units);
}

function chartTraces(investigation: Investigation, monthly: Series[] | null): ScatterTrace[] {
  const { variable, requested } = investigation;
  const traces: ScatterTrace[] = [];
  investigation.results.forEach((result, index) => {
    const style = placeStyle(index);
    const name = plotlyText(result.place.name);
    const monthlySeries = monthly?.[index];
    if (monthlySeries !== undefined) {
      traces.push({
        type: "scatter",
        // A season's months are months apart from one year to the next, so they are not joined.
        mode: requested.season === "annual" ? "lines" : "markers",
        name: `${name}: monthly values`,
        legendgroup: name,
        x: monthlySeries.values.map((point) => `${point.date}-${MID_MONTH_DAY}`),
        y: monthlySeries.values.map((point) => point.value),
        text: monthlySeries.values.map((point) =>
          point.value === null
            ? `${name}<br>${point.date}: no value`
            : `${name}<br>${point.date}: ${valueText(point.value, variable)}`,
        ),
        hovertemplate: HOVER_TEXT_ONLY,
        connectgaps: false,
        opacity: 0.45,
        line: { color: style.color, width: 1 },
        marker: { color: style.color, size: 4 },
      });
    }
    traces.push({
      type: "scatter",
      mode: "lines+markers",
      name: `${name}: yearly values`,
      legendgroup: name,
      x: result.series.map((point) => yearDate(point.year, requested.season)),
      y: result.series.map((point) => point.value),
      text: result.series.map((point) =>
        point.value === null
          ? `${name}<br>${point.year}: no value`
          : `${name}<br>${point.year}: ${valueText(point.value, variable)}`,
      ),
      hovertemplate: HOVER_TEXT_ONLY,
      connectgaps: false,
      line: { color: style.color, width: 1.5 },
      marker: {
        color: style.color,
        size: 8,
        symbol: style.plotlySymbol,
        line: { color: SURFACE, width: 1 },
      },
    });
    const trend = result.trend;
    if (trend !== null) {
      const ends: [number, number][] = [
        [trend.first_year, trend.line[0]],
        [trend.last_year, trend.line[1]],
      ];
      traces.push({
        type: "scatter",
        mode: "lines",
        name: `${name}: trend line`,
        legendgroup: name,
        x: ends.map(([year]) => yearDate(year, requested.season)),
        y: ends.map(([, value]) => value),
        text: ends.map(([year, value]) => `${name}<br>Trend line in ${year}: ${valueText(value, variable)}`),
        hovertemplate: HOVER_TEXT_ONLY,
        line: { color: style.color, width: 2.5, dash: "dash" },
      });
    }
  });
  return traces;
}

function chartLayout(variable: VariableSummary): Layout {
  return {
    ...BASE_LAYOUT,
    height: CHART_HEIGHT_PX,
    xaxis: { ...AXIS_STYLE, type: "date", title: { text: "Year" } },
    yaxis: { ...AXIS_STYLE, title: { text: `${variable.name} (${variable.units})` } },
  };
}

function placeSummary(result: PlaceResult, variable: VariableSummary): string {
  const { place, series, trend, verdict } = result;
  const firstYear = series[0]?.year;
  const lastYear = series.at(-1)?.year;
  const parts = [`${place.name}: yearly values from ${firstYear ?? "?"} to ${lastYear ?? "?"}.`];
  const missing = series.filter((point) => point.value === null).map((point) => String(point.year));
  if (missing.length === series.length) {
    parts.push("No year has a value.");
  } else if (missing.length > 0) {
    parts.push(`No value in ${joinWords(missing)}.`);
  }
  if (trend !== null) {
    const [start, end] = trend.line;
    parts.push(
      `The trend line runs from ${valueText(start, variable)} in ${trend.first_year} ` +
        `to ${valueText(end, variable)} in ${trend.last_year}.`,
      // The chart draws one line; how sure its rate is, the words say, in the evidence panel's numbers.
      trend.sen_ci95 === null
        ? `Its rate is ${formatRatePerDecade(trend.sen_slope, variable)}; no 95% confidence interval ` +
            "is given, because its coverage under serial dependence has not been validated."
        : `Its rate is ${formatRatePerDecade(trend.sen_slope, variable)}; the 95% confidence interval ` +
            `of the rate runs from ${formatSignedRate(trend.sen_ci95[0], variable.decimals)} ` +
            `to ${formatRatePerDecade(trend.sen_ci95[1], variable)}.`,
    );
  } else if (verdict.kind === "too_few_years") {
    parts.push("There is no trend line, because there are too few complete years to test.");
  }
  return parts.join(" ");
}

function chartSummary(investigation: Investigation): string[] {
  const { variable } = investigation;
  return [
    `Chart of ${variable.name.toLowerCase()} in ${variable.units}.`,
    ...investigation.results.map((result) => placeSummary(result, variable)),
  ];
}

function YearlyTable({ investigation }: TrendChartProps): JSX.Element {
  const { variable, results } = investigation;
  const years = results[0]?.series.map((point) => point.year) ?? [];
  return (
    <div className="table-scroll">
      <table className="data-table">
        <caption>
          {variable.name} ({variable.units}), {seasonAverageText(investigation.requested.season)}
        </caption>
        <thead>
          <tr>
            <th scope="col">Year</th>
            {results.map((result, index) => (
              <th scope="col" key={index}>
                {result.place.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {years.map((year, row) => (
            <tr key={year}>
              <th scope="row">{year}</th>
              {results.map((result, index) => {
                const value = result.series[row]?.value ?? null;
                return (
                  <td key={index}>{value === null ? "No value" : formatNumber(value, variable.decimals)}</td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
