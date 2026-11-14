import { useEffect, useMemo } from "react";
import type { JSX } from "react";
import { getOverview } from "../api";
import type { OverviewRow, PlaceOverview } from "../api";
import { buildOverviewQuery } from "../caseUrl";
import type { CasePlace, OverviewParams } from "../caseUrl";
import { formatCoordinates } from "../format";
import { useGlobePlaces } from "../globeContext";
import { followInApp } from "../links";
import type { MapPlace } from "../mapCell";
import { overviewThemes, rowCaseUrl } from "../overviewRows";
import { periodText } from "../seasons";
import { useRequest } from "../useRequest";
import { CaseLayout } from "./CaseLayout";
import { ProgressLine } from "./ProgressLine";

const APP_NAME = "Trend Detective";

interface PlaceOverviewViewProps {
  params: OverviewParams;
  pickedPoint: CasePlace | null;
  onOpenPage: (url: string) => void;
  onPick: (point: CasePlace) => void;
}

/**
 * What is changing at one place (spec 7, "What is changing here?"): every catalogue variable's
 * descriptive rate, grouped by theme in the catalogue's order and never ranked. Each line is the
 * API's sentence; the variable's name opens it as an ordinary case.
 */
export function PlaceOverviewView({
  params,
  pickedPoint,
  onOpenPage,
  onPick,
}: PlaceOverviewViewProps): JSX.Element {
  const request = useRequest(`overview:${buildOverviewQuery(params)}`, (signal) =>
    getOverview(params, signal),
  );
  const { state } = request;
  const overview = state.status === "done" ? state.value : state.status === "loading" ? state.stale : null;
  const name = params.place.name ?? formatCoordinates(params.place.lat, params.place.lon);
  const mapPlaces = useMemo<MapPlace[]>(
    () => [{ name, lat: params.place.lat, lon: params.place.lon }],
    [name, params.place.lat, params.place.lon],
  );
  useGlobePlaces(mapPlaces, pickedPoint, onPick);

  useEffect(() => {
    document.title = `What is changing in ${name} · ${APP_NAME}`;
    return () => {
      document.title = APP_NAME;
    };
  }, [name]);

  return (
    <CaseLayout
      answer={
        <>
          <ProgressLine active={state.status === "loading"} label="Getting the data for every variable…" />
          {state.status === "failed" ? (
            <p className="notice notice-error" role="alert">
              The overview could not be loaded. {state.error.message}{" "}
              <button type="button" className="button button-secondary" onClick={request.retry}>
                Try again
              </button>
            </p>
          ) : null}
          <div className="live-region" aria-live="polite">
            {overview !== null ? <OverviewAnswer overview={overview} onOpenPage={onOpenPage} /> : null}
          </div>
        </>
      }
      side={null}
      main={overview !== null ? <OverviewSources overview={overview} /> : null}
    />
  );
}

interface OverviewAnswerProps {
  overview: PlaceOverview;
  onOpenPage: (url: string) => void;
}

export function OverviewAnswer({ overview, onOpenPage }: OverviewAnswerProps): JSX.Element {
  const themes = overviewThemes(overview.rows);
  return (
    <>
      <section className="panel verdict-card" aria-labelledby="overview-heading">
        <h2 id="overview-heading">What is changing in {overview.name}?</h2>
        <p className="panel-intro">
          {formatCoordinates(overview.lat, overview.lon)} · {periodText(overview.requested)}. Each variable
          describes the grid cell that contains the place, over its own record within this period.
        </p>
        <p className="verdict-note">{overview.note}</p>
      </section>
      {themes.map(({ theme, rows }) => (
        <section
          key={theme}
          className="panel sheet"
          aria-labelledby={`overview-${theme.replaceAll(" ", "-")}`}
        >
          <h2 id={`overview-${theme.replaceAll(" ", "-")}`}>
            {theme.charAt(0).toUpperCase() + theme.slice(1)}
          </h2>
          <ul className="plain-list">
            {rows.map((row) => (
              <OverviewLine key={row.variable.id} row={row} overview={overview} onOpenPage={onOpenPage} />
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}

function OverviewLine({
  row,
  overview,
  onOpenPage,
}: {
  row: OverviewRow;
  overview: PlaceOverview;
  onOpenPage: (url: string) => void;
}): JSX.Element {
  const url = rowCaseUrl(row, overview);
  return (
    <li>
      <a href={url} onClick={(event) => followInApp(event, url, onOpenPage)}>
        {row.variable.name}
      </a>
      : {row.sentence}
    </li>
  );
}

function OverviewSources({ overview }: { overview: PlaceOverview }): JSX.Element {
  return (
    <section className="panel" aria-labelledby="overview-data-heading">
      <h2 id="overview-data-heading">Data</h2>
      <p className="panel-note">
        This overview reads the latest data and pins no evidence; a variable opened as a case pins its own.
      </p>
      <ul className="plain-list">
        {overview.sources.map((source, index) => (
          <li key={index}>
            {source.name}, API {source.version}, accessed {source.accessed}
          </li>
        ))}
      </ul>
    </section>
  );
}
