import type { ClickPoint, Layout, ScatterTrace } from "plotly.js-basic-dist-min";
import { lazy, Suspense, useMemo, useState } from "react";
import type { JSX } from "react";
import { getCase } from "../api";
import type { Investigation, ScanPoint, VariableSummary } from "../api";
import { buildCaseQuery } from "../caseUrl";
import type { CaseParams } from "../caseUrl";
import { AXIS_LINE, AXIS_STYLE, BASE_LAYOUT, HOVER_TEXT_ONLY, plotlyText } from "../chartStyle";
import { PERIOD_CAUTION } from "../definitions";
import { formatPValue, formatSignedRate, withUnits } from "../format";
import { caseFromFirstYear, isSignificant, yearRuns } from "../periodScan";
import { placeStyle } from "../placeStyles";
import { useRequest } from "../useRequest";
import { ShapeSwatch } from "./ShapeSwatch";

const PlotlyChart = lazy(() => import("./PlotlyChart"));

const CHART_HEIGHT_PX = 320;
const CURRENT_START_COLOUR = "#6b5846";

interface PeriodExplorerProps {
  /** The case on screen. */
  params: CaseParams;
  /** The case's answer, for its variable and the period it used. */
  investigation: Investigation;
  /** Opens a case: the same case from the first year the user chose, which reloads through /api/case. */
  onOpenCase: (params: CaseParams) => void;
}

/**
 * How the trend depends on the first year of the period (spec 3, "Explorable significance").
 * It asks for the case over the full record with the scan, and only draws the overview: the
 * verdict always comes from the case itself (spec 10).
 */
export function PeriodExplorer({ params, investigation, onOpenCase }: PeriodExplorerProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const { variable, requested } = investigation;
  const scanParams = useMemo(() => fullRecordScan(params, requested.to), [params, requested.to]);
  const scan = useRequest(open ? buildCaseQuery(scanParams) : null, (signal) => getCase(scanParams, signal));
  const scanned = scan.state.status === "done" ? scan.state.value : null;

  return (
    <section className="panel" aria-labelledby="explorer-heading">
      <details className="explorer" onToggle={(event) => setOpen(event.currentTarget.open)}>
        <summary>
          <h2 id="explorer-heading">Explore the period</h2>
          <span className="summary-hint">See how the trend changes with the first year</span>
        </summary>
        <p className="caution">
          <strong>Caution:</strong> {PERIOD_CAUTION}
        </p>
        <p className="status-text" role="status">
          {scan.state.status === "loading" ? "Testing every first year…" : null}
        </p>
        {scan.state.status === "failed" ? (
          <p className="notice notice-error" role="alert">
            The overview could not be loaded. {scan.state.error.message}{" "}
            <button type="button" className="button button-secondary" onClick={scan.retry}>
              Try again
            </button>
          </p>
        ) : null}
        {scanned !== null ? (
          <ScanView
            scanned={scanned}
            currentStart={requested.from}
            variable={variable}
            onChooseStart={(year) => onOpenCase(caseFromFirstYear(params, year))}
          />
        ) : null}
      </details>
    </section>
  );
}

function fullRecordScan(params: CaseParams, to: number): CaseParams {
  return { ...params, from: undefined, to, scan: true };
}

interface ScanViewProps {
  scanned: Investigation;
  currentStart: number;
  variable: VariableSummary;
  onChooseStart: (year: number) => void;
}

function ScanView({ scanned, currentStart, variable, onChooseStart }: ScanViewProps): JSX.Element {
  const scans = useMemo(() => scanned.results.map((result) => result.trend?.scan ?? []), [scanned]);
  const data = useMemo(() => scanTraces(scanned, scans), [scanned, scans]);
  const layout = useMemo(
    () => scanLayout(variable, scanned.requested.to, currentStart),
    [variable, scanned, currentStart],
  );
  const startYears = [...new Set(scans.flat().map((point) => point.start))].sort((a, b) => a - b);
  const summaries = scanned.results.map((result, index) =>
    scanSummary(result.place.name, scans[index] ?? []),
  );
  const singlePlaceScan = scans.length === 1 ? scans[0] : undefined;

  if (startYears.length === 0) {
    return <p>No first year leaves enough complete years to test, so there is nothing to explore.</p>;
  }
  const handleClick = (point: ClickPoint): void => {
    if (typeof point.x === "number") onChooseStart(point.x);
  };
  return (
    <>
      <p className="panel-intro">
        Each point is the descriptive rate of change from that first year to {scanned.requested.to}.
        Significance is not assessed in the period scan. The dashed line marks the case&apos;s first year.
        Choose a point or a year to reload the case from that year.
      </p>
      <Suspense fallback={<div className="chart-placeholder">Loading the chart…</div>}>
        <PlotlyChart
          data={data}
          layout={layout}
          description={summaries.join(" ")}
          onPointClick={handleClick}
        />
      </Suspense>
      <ul className="chart-summary">
        {summaries.map((summary, index) => (
          <li key={index}>
            <ShapeSwatch index={index} /> {summary}
          </li>
        ))}
      </ul>
      <div className="field-row">
        <label className="field">
          <span className="field-label">First year of the case</span>
          <select
            value={startYears.includes(currentStart) ? String(currentStart) : ""}
            onChange={(event) => onChooseStart(Number(event.target.value))}
          >
            {startYears.includes(currentStart) ? null : <option value="">{currentStart}</option>}
            {startYears.map((year) => (
              <option key={year} value={year}>
                {startOptionText(year, singlePlaceScan, variable)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="button button-secondary"
          disabled={currentStart <= variable.record_start}
          onClick={() => onChooseStart(variable.record_start)}
        >
          Use the full record
        </button>
      </div>
    </>
  );
}

function rateText(rate: number, variable: VariableSummary): string {
  return `${withUnits(formatSignedRate(rate, variable.decimals), variable.rate_units)} per decade`;
}

function significanceWord(point: ScanPoint): string {
  if (point.mk_p === null) return "significance not assessed";
  return isSignificant(point) ? "significant" : "not significant";
}

function startOptionText(year: number, scan: ScanPoint[] | undefined, variable: VariableSummary): string {
  const point = scan?.find((candidate) => candidate.start === year);
  if (point === undefined) return String(year);
  return `${year}: ${rateText(point.sen_slope, variable)}, ${significanceWord(point)}`;
}

function scanSummary(placeName: string, scan: readonly ScanPoint[]): string {
  if (scan.every((point) => point.mk_p === null)) {
    return `${placeName}: descriptive rates only; significance is not assessed in a period scan.`;
  }
  const significant = scan.filter(isSignificant).map((point) => point.start);
  if (significant.length === 0) return `${placeName}: no first year gives a significant trend.`;
  return `${placeName}: the trend is significant from the first years ${yearRuns(significant)}.`;
}

function scanTraces(scanned: Investigation, scans: ScanPoint[][]): ScatterTrace[] {
  const { variable } = scanned;
  return scanned.results.map((result, index) => {
    const style = placeStyle(index);
    const scan = scans[index] ?? [];
    const name = plotlyText(result.place.name);
    return {
      type: "scatter",
      mode: "lines+markers",
      name,
      x: scan.map((point) => point.start),
      y: scan.map((point) => point.sen_slope),
      text: scan.map(
        (point) =>
          `${name}<br>From ${point.start}: ${rateText(point.sen_slope, variable)}, ` +
          (point.mk_p === null
            ? "Significance not assessed"
            : `p = ${formatPValue(point.mk_p)}, ${significanceWord(point)}`),
      ),
      hovertemplate: HOVER_TEXT_ONLY,
      line: { color: style.color, width: 1.5 },
      // Significance is shown by the marker's fill, so it never depends on colour alone.
      marker: {
        color: style.color,
        size: 9,
        symbol: scan.map((point) =>
          isSignificant(point) ? style.plotlySymbol : `${style.plotlySymbol}-open`,
        ),
        line: { color: style.color, width: 1.5 },
      },
    };
  });
}

function scanLayout(variable: VariableSummary, to: number, currentStart: number): Layout {
  const rateUnits = variable.rate_units === "" ? "per decade" : `${variable.rate_units} per decade`;
  return {
    ...BASE_LAYOUT,
    height: CHART_HEIGHT_PX,
    xaxis: {
      ...AXIS_STYLE,
      type: "linear",
      tickformat: "d",
      title: { text: `First year (every period ends in ${to})` },
    },
    yaxis: {
      ...AXIS_STYLE,
      zeroline: true,
      zerolinecolor: AXIS_LINE,
      // The units go on a second line, so a long title such as "percentage points per decade"
      // still fits the height of the chart.
      title: { text: `Rate of change<br>(${rateUnits})` },
    },
    shapes: [
      {
        type: "line",
        xref: "x",
        yref: "paper",
        x0: currentStart,
        x1: currentStart,
        y0: 0,
        y1: 1,
        line: { color: CURRENT_START_COLOUR, width: 1.5, dash: "dash" },
      },
    ],
  };
}
