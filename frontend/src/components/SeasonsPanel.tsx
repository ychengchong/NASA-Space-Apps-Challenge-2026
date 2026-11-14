import type { Layout, ScatterTrace } from "plotly.js-basic-dist-min";
import { lazy, Suspense, useMemo, useState } from "react";
import type { JSX } from "react";
import { getSeasons } from "../api";
import type { Investigation, PlaceSeasons, SeasonRate, SeasonRates, VariableSummary } from "../api";
import { buildCaseQuery } from "../caseUrl";
import type { CaseParams } from "../caseUrl";
import { AXIS_LINE, AXIS_STYLE, BASE_LAYOUT, HOVER_TEXT_ONLY, plotlyText } from "../chartStyle";
import { formatRatePerDecade } from "../format";
import { followInApp } from "../links";
import { placeStyle } from "../placeStyles";
import { casePageUrl } from "../route";
import { SEASON_LABELS, SEASON_SHORT_LABELS } from "../seasons";
import { chartDescription, significanceText, yearsText } from "../seasonRows";
import { useRequest } from "../useRequest";
import { ShapeSwatch } from "./ShapeSwatch";

const PlotlyChart = lazy(() => import("./PlotlyChart"));

const CHART_HEIGHT_PX = 300;

interface SeasonsPanelProps {
  /** The case on screen. */
  params: CaseParams;
  /** The case's answer, for its variable and its season. */
  investigation: Investigation;
  /** Opens a page of the app, such as a season as an ordinary case. */
  onOpenPage: (url: string) => void;
}

/**
 * The rate for all months and for each season side by side (spec 7, "All seasons at once"). It
 * asks /api/seasons only once opened, and draws what the API returns: rates, years and sentences.
 */
export function SeasonsPanel({ params, investigation, onOpenPage }: SeasonsPanelProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const seasons = useRequest(open ? `seasons:${buildCaseQuery(params)}` : null, (signal) =>
    getSeasons(params, signal),
  );
  const answer = seasons.state.status === "done" ? seasons.state.value : null;
  return (
    <section className="panel" aria-labelledby="seasons-heading">
      <details className="explorer" onToggle={(event) => setOpen(event.currentTarget.open)}>
        <summary>
          <h2 id="seasons-heading">Compare the seasons</h2>
          <span className="summary-hint">The rate for all months and for each season, side by side</span>
        </summary>
        <p className="status-text" role="status">
          {seasons.state.status === "loading" ? "Estimating the rate of every season…" : null}
        </p>
        {seasons.state.status === "failed" ? (
          <p className="notice notice-error" role="alert">
            The seasons could not be loaded. {seasons.state.error.message}{" "}
            <button type="button" className="button button-secondary" onClick={seasons.retry}>
              Try again
            </button>
          </p>
        ) : null}
        {answer !== null ? (
          <SeasonsView
            answer={answer}
            current={investigation.requested.season}
            seasonUrl={(season) => casePageUrl({ ...params, season })}
            onOpenPage={onOpenPage}
          />
        ) : null}
      </details>
    </section>
  );
}

interface SeasonsViewProps {
  answer: SeasonRates;
  current: SeasonRate["season"];
  seasonUrl: (season: SeasonRate["season"]) => string;
  onOpenPage: (url: string) => void;
}

export function SeasonsView({ answer, current, seasonUrl, onOpenPage }: SeasonsViewProps): JSX.Element {
  const { variable } = answer;
  const data = useMemo(() => seasonTraces(answer), [answer]);
  const layout = useMemo(() => seasonLayout(variable), [variable]);
  const description = chartDescription(answer);
  const several = answer.places.length > 1;
  return (
    <>
      <p className="panel-intro">{answer.note}</p>
      <Suspense fallback={<div className="chart-placeholder">Loading the chart…</div>}>
        <PlotlyChart data={data} layout={layout} description={description} />
      </Suspense>
      {answer.places.map((place, index) => (
        <div key={index}>
          {several ? (
            <h3>
              <ShapeSwatch index={index} /> {place.place.name}
            </h3>
          ) : null}
          <SeasonTable
            place={place}
            variable={variable}
            current={current}
            seasonUrl={seasonUrl}
            onOpenPage={onOpenPage}
          />
          <ul className="chart-summary">
            {place.rates.map((rate) => (
              <li key={rate.season}>
                <ShapeSwatch index={index} /> {rate.sentence}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}

interface SeasonTableProps {
  place: PlaceSeasons;
  variable: VariableSummary;
  current: SeasonRate["season"];
  seasonUrl: (season: SeasonRate["season"]) => string;
  onOpenPage: (url: string) => void;
}

function SeasonTable({ place, variable, current, seasonUrl, onOpenPage }: SeasonTableProps): JSX.Element {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <caption>
          {variable.name}, {place.place.name}
        </caption>
        <thead>
          <tr>
            <th scope="col">Months</th>
            <th scope="col">Years used</th>
            <th scope="col">Rate per decade</th>
            <th scope="col">Significance</th>
            <th scope="col">Case</th>
          </tr>
        </thead>
        <tbody>
          {place.rates.map((rate) => (
            <tr key={rate.season}>
              <th scope="row">{SEASON_LABELS[rate.season]}</th>
              <td>{yearsText(rate)}</td>
              <td>{rate.sen_slope === null ? "No rate" : formatRatePerDecade(rate.sen_slope, variable)}</td>
              <td>{significanceText(rate)}</td>
              <td>
                {rate.season === current ? (
                  "This case"
                ) : (
                  <a
                    href={seasonUrl(rate.season)}
                    aria-label={`Open ${SEASON_LABELS[rate.season]} as a case`}
                    onClick={(event) => followInApp(event, seasonUrl(rate.season), onOpenPage)}
                  >
                    Open
                  </a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function seasonTraces(answer: SeasonRates): ScatterTrace[] {
  const { variable } = answer;
  return answer.places.map((place, index) => {
    const style = placeStyle(index);
    const name = plotlyText(place.place.name);
    return {
      type: "scatter",
      mode: "markers",
      name,
      x: place.rates.map((rate) => SEASON_SHORT_LABELS[rate.season]),
      y: place.rates.map((rate) => rate.sen_slope),
      text: place.rates.map((rate) =>
        rate.sen_slope === null
          ? `${name}<br>${SEASON_LABELS[rate.season]}: no rate`
          : `${name}<br>${SEASON_LABELS[rate.season]}: ${formatRatePerDecade(rate.sen_slope, variable)}`,
      ),
      hovertemplate: HOVER_TEXT_ONLY,
      marker: {
        color: style.color,
        size: 11,
        symbol: style.plotlySymbol,
        line: { color: style.color, width: 1.5 },
      },
    };
  });
}

function seasonLayout(variable: VariableSummary): Layout {
  const rateUnits = variable.rate_units === "" ? "per decade" : `${variable.rate_units} per decade`;
  return {
    ...BASE_LAYOUT,
    height: CHART_HEIGHT_PX,
    xaxis: { ...AXIS_STYLE, type: "category" },
    yaxis: {
      ...AXIS_STYLE,
      zeroline: true,
      zerolinecolor: AXIS_LINE,
      // The rates are drawn against zero, so zero is always in the range.
      rangemode: "tozero",
      title: { text: `Rate of change<br>(${rateUnits})` },
    },
  };
}
