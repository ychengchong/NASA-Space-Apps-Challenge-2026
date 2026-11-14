import { useEffect, useMemo, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ApiError, getMap } from "../api";
import type { Box, ExampleCase, MapCell, TrendMap, VariableSummary } from "../api";
import { buildMapQuery, parseMapQuery } from "../caseUrl";
import type { MapParams } from "../caseUrl";
import { scaleLimit } from "../colourScale";
import { PERIOD_CAUTION, POWER_ACKNOWLEDGEMENT, REGION_MAP_NOTE } from "../definitions";
import { formatCoordinates, formatPValue, formatRatePerDecade } from "../format";
import { useGlobe, useGlobeRegion } from "../globeContext";
import { followInApp } from "../links";
import { boxText, draftFromMapQuery, mapFromDraft } from "../mapDraft";
import type { BoxText, MapDraft } from "../mapDraft";
import { casePageUrl, mapPageUrl } from "../route";
import { isSeason, SEASON_LABELS, SEASON_ORDER, seasonMonthsText } from "../seasons";
import { useRequest } from "../useRequest";
import type { RequestState } from "../useRequest";
import { CaseActions } from "./CaseActions";
import { CaseLayout } from "./CaseLayout";
import { ExampleCases } from "./ExampleCases";
import { MapLegend, StageLegend } from "./MapLegend";
import { ProgressLine } from "./ProgressLine";
import { SettingsFold } from "./SettingsFold";
import { VerdictSkeleton } from "./Skeleton";
import { StageNote } from "./StageNote";
import { PlaceVerdict } from "./VerdictCard";
import { WordsUsedHere } from "./WordsUsedHere";

const APP_NAME = "Trend Detective";

/** A map that is already in hand, such as one the AI ran, keyed by its parameter string. */
export interface PreloadedMap {
  key: string;
  map: TrendMap;
}

interface RegionViewProps {
  /** The map page's query string, without the leading "?". */
  query: string;
  variables: RequestState<VariableSummary[]>;
  /** The saved example cases, which still open when NASA's data service is not answering. */
  examples: RequestState<ExampleCase[]>;
  preloaded: PreloadedMap | null;
  /** The AI's notes, when a conversation is going. */
  notes: JSX.Element | null;
  /** Opens a page, such as a cell's case, as a new page. */
  onOpenPage: (url: string) => void;
  /** Shows another map, keeping this page's place on screen. */
  onShowMap: (url: string) => void;
  /** Replaces the address with the map the API answered for, period filled in. */
  onNormalised: (url: string) => void;
}

/**
 * The region view of `/map` (spec 7, "Region view", and spec 12, stage 6): the trend of every
 * grid cell in a box of at most 10° by 10°, drawn on the globe, the verdict for the area mean,
 * and the controls to choose the variable, period, season and box.
 */
export function RegionView(props: RegionViewProps): JSX.Element {
  const { query, preloaded } = props;
  const parsed = useMemo(() => parseMapQuery(query), [query]);
  const params = parsed.ok ? parsed.value : null;
  const key = params === null ? null : buildMapQuery(params);
  const request = useRequest(key, (signal) => loadMap(params, preloaded, signal), {
    answerKey: (trendMap) => buildMapQuery(paramsOfMap(trendMap)),
    onDone: (trendMap) => {
      const answered = paramsOfMap(trendMap);
      if (buildMapQuery(answered) !== key) props.onNormalised(mapPageUrl(answered));
    },
  });
  const { state } = request;
  const trendMap = shownMap(state);
  const loading = state.status === "loading";
  const limit = useMemo(
    () => (trendMap === null ? 0 : scaleLimit(trendMap.cells.map((cell) => cell.sen_slope))),
    [trendMap],
  );

  const [form, setForm] = useState(() => ({
    query,
    draft: draftFromMapQuery(query),
    error: null as string | null,
  }));
  // The settings follow the address: a new map, the back button or the AI resets them.
  const current = form.query === query ? form : { query, draft: draftFromMapQuery(query), error: null };
  const setDraft = (draft: MapDraft): void => setForm({ query, draft, error: null });
  const [drawing, setDrawing] = useState(false);

  const submit = (draft: MapDraft): void => {
    const result = mapFromDraft(draft);
    if (!result.ok) {
      setForm({ query, draft, error: result.reason });
      return;
    }
    setDrawing(false);
    setForm({ query, draft, error: null });
    props.onShowMap(mapPageUrl(result.value));
  };

  const openCell = (cell: MapCell): void => {
    if (trendMap === null) return;
    props.onOpenPage(cellCaseUrl(trendMap, cell));
  };

  const globe = useGlobe();
  useGlobeRegion({
    box: params?.box ?? null,
    trendMap: state.status === "failed" ? null : trendMap,
    scaleLimit: limit,
    drawing,
    onBoxDrawn: (box) => submit({ ...current.draft, box: boxText(box) }),
    onOpenCell: openCell,
  });

  useEffect(() => {
    document.title = trendMap === null ? APP_NAME : `Map of ${trendMap.variable.name} · ${APP_NAME}`;
    return () => {
      document.title = APP_NAME;
    };
  }, [trendMap]);

  const resultsClass = loading ? "case-results is-stale" : "case-results";
  return (
    <CaseLayout
      side={
        <SettingsFold
          label="Change this map"
          hint="Variable, period, season and box"
          needed={params === null || current.error !== null || state.status === "failed"}
        >
          <MapSettings
            draft={current.draft}
            error={current.error}
            variables={props.variables}
            onChange={setDraft}
            onSubmit={() => submit(current.draft)}
          />
        </SettingsFold>
      }
      answer={
        <>
          {params === null ? <MapIntro reason={query === "" || parsed.ok ? null : parsed.reason} /> : null}
          <ProgressLine active={loading} label="Getting the data and testing every grid cell…" />
          {loading && trendMap === null ? <VerdictSkeleton /> : null}
          {state.status === "failed" ? (
            <MapProblem
              error={state.error}
              onRetry={request.retry}
              examples={props.examples}
              onOpenExample={props.onOpenPage}
            />
          ) : null}
          {/* In the page while empty, so screen readers announce the verdict when it arrives. */}
          <div className="live-region" aria-live="polite">
            {trendMap !== null && state.status !== "failed" ? (
              <div className={resultsClass} aria-busy={loading}>
                <AreaVerdict trendMap={trendMap} />
              </div>
            ) : null}
          </div>
          {trendMap !== null && state.status !== "failed" ? (
            <>
              {!loading ? <CaseActions key={key} subject="map" /> : null}
              <StageNote>
                <StageLegend trendMap={trendMap} limit={limit} />
              </StageNote>
            </>
          ) : null}
          {props.notes}
        </>
      }
      main={
        <>
          <section className="panel" aria-labelledby="region-map-heading">
            <div className="panel-heading-row">
              <h2 id="region-map-heading">Trend in each grid cell</h2>
              <button
                type="button"
                className="button button-secondary"
                aria-pressed={drawing}
                disabled={globe.handle === null}
                onClick={() => setDrawing((on) => !on)}
              >
                {drawing ? "Stop drawing" : "Draw a box"}
              </button>
            </div>
            <p className="panel-intro">{mapIntroText(trendMap)}</p>
            <p className="status-text" role="status">
              {drawing
                ? "Drag on the globe to draw a box. It snaps to whole degrees and stops at 10° on each side."
                : ""}
            </p>
            {trendMap !== null && state.status !== "failed" ? (
              <MapLegend variable={trendMap.variable} limit={limit} />
            ) : null}
          </section>
          {trendMap !== null && state.status !== "failed" ? (
            <MapEvidence trendMap={trendMap} onOpenPage={props.onOpenPage} />
          ) : null}
        </>
      }
    />
  );
}

function loadMap(
  params: MapParams | null,
  preloaded: PreloadedMap | null,
  signal: AbortSignal,
): Promise<TrendMap> {
  if (params === null) return Promise.reject(new ApiError("bad_request", "The map has no settings yet."));
  if (preloaded !== null && preloaded.key === buildMapQuery(params)) return Promise.resolve(preloaded.map);
  return getMap(params, signal);
}

function shownMap(state: RequestState<TrendMap>): TrendMap | null {
  if (state.status === "done") return state.value;
  if (state.status === "loading") return state.stale;
  return null;
}

/** The map the API answered for: its clamped period and its rounded box. */
function paramsOfMap(trendMap: TrendMap): MapParams {
  return {
    variable: trendMap.variable.id,
    from: trendMap.requested.from,
    to: trendMap.requested.to,
    season: trendMap.requested.season,
    box: trendMap.box,
  };
}

/** A cell opens as an ordinary case at its grid point, with the map's period and season. */
function cellCaseUrl(trendMap: TrendMap, cell: MapCell): string {
  return casePageUrl({
    variable: trendMap.variable.id,
    places: [{ lat: cell.lat, lon: cell.lon }],
    from: trendMap.requested.from,
    to: trendMap.requested.to,
    season: trendMap.requested.season,
  });
}

function mapIntroText(trendMap: TrendMap | null): string {
  if (trendMap === null) return "The globe will colour each grid cell by its own trend.";
  const { variable, requested } = trendMap;
  return (
    `${variable.name} from ${requested.from} to ${requested.to}, ${seasonMonthsText(requested.season)}, ` +
    "coloured on the globe. Click a cell to open it as a case."
  );
}

function MapIntro({ reason }: { reason: string | null }): JSX.Element {
  if (reason !== null) {
    return (
      <div className="notice notice-error" role="alert">
        <h2>This link does not open a map</h2>
        <p>{reason}</p>
        <p>Choose the map settings to make a new one.</p>
      </div>
    );
  }
  return (
    <section className="panel" aria-labelledby="region-intro-heading">
      <h2 id="region-intro-heading">Region map</h2>
      <p>
        Test every grid cell in a box of up to 10° by 10° the same way as a place. Choose a variable and a box
        in the map settings, or draw a box on the globe.
      </p>
    </section>
  );
}

interface MapProblemProps {
  error: ApiError;
  onRetry: () => void;
  examples: RequestState<ExampleCase[]>;
  onOpenExample: (url: string) => void;
}

/** Why a map could not load, with the next step, as CaseProblem does for a case (spec 3). */
function MapProblem({ error, onRetry, examples, onOpenExample }: MapProblemProps): JSX.Element {
  if (error.code === "source_unavailable") {
    return (
      <div className="notice notice-warning" role="alert">
        <h2>NASA&apos;s data service is not answering</h2>
        <p>{error.message}</p>
        <p>
          The data for this map is not saved here yet, so it cannot open right now. Try again in a minute. The
          example cases are saved, so they still open, each as a case rather than a map.
        </p>
        <p>
          <button type="button" className="button button-primary" onClick={onRetry}>
            Try again
          </button>
        </p>
        <ExampleCases examples={examples} onOpen={onOpenExample} />
      </div>
    );
  }
  if (isTemporary(error)) {
    return (
      <div className="notice notice-warning" role="alert">
        <h2>The map could not load</h2>
        <p>{error.message}</p>
        <p>
          <button type="button" className="button button-primary" onClick={onRetry}>
            Try again
          </button>
        </p>
      </div>
    );
  }
  return (
    <div className="notice notice-error" role="alert">
      <h2>This map cannot be made</h2>
      <p>{error.message}</p>
      <p>Change the map settings to try again.</p>
    </div>
  );
}

function isTemporary(error: ApiError): boolean {
  return (
    error.code === "rate_limited" ||
    error.code === "network_error" ||
    error.code === "bad_response" ||
    error.code === "internal_error"
  );
}

function AreaVerdict({ trendMap }: { trendMap: TrendMap }): JSX.Element {
  return (
    <section className="panel verdict-card" aria-labelledby="area-verdict-heading">
      <h2 id="area-verdict-heading">Verdict for the whole box</h2>
      <PlaceVerdict result={trendMap.area_mean} index={0} variable={trendMap.variable} showName={false} />
      <p className="panel-note verdict-method">
        All the grid cells averaged into one series, each weighted by the cosine of its latitude because cells
        shrink toward the poles, then tested like a place.
      </p>
    </section>
  );
}

function MapEvidence({
  trendMap,
  onOpenPage,
}: {
  trendMap: TrendMap;
  onOpenPage: (url: string) => void;
}): JSX.Element {
  const { variable } = trendMap;
  return (
    <section className="panel" aria-labelledby="map-evidence-heading">
      <details className="evidence">
        <summary>
          <h2 id="map-evidence-heading">Evidence</h2>
          <span className="summary-hint">Every grid cell, the method and the data behind the map</span>
        </summary>

        <h3>Steps taken</h3>
        <ol className="steps">
          {trendMap.steps.map((step, index) => (
            <li key={index}>{step}</li>
          ))}
        </ol>

        <h3>Every grid cell</h3>
        <p>Open a cell to see it as an ordinary case, judged by the ordinary rule. {REGION_MAP_NOTE}</p>
        <div className="table-scroll">
          <table className="data-table">
            <caption>
              {variable.name}, {trendMap.requested.from} to {trendMap.requested.to}
            </caption>
            <thead>
              <tr>
                <th scope="col">Grid point</th>
                <th scope="col">Rate of change</th>
                <th scope="col">p-value</th>
                <th scope="col">Marked</th>
              </tr>
            </thead>
            <tbody>
              {trendMap.cells.map((cell) => {
                const url = cellCaseUrl(trendMap, cell);
                return (
                  <tr key={`${cell.lat},${cell.lon}`}>
                    <th scope="row">
                      <a href={url} onClick={(event) => followInApp(event, url, onOpenPage)}>
                        {formatCoordinates(cell.lat, cell.lon)}
                      </a>
                    </th>
                    <td>
                      {cell.sen_slope === null ? "No result" : formatRatePerDecade(cell.sen_slope, variable)}
                    </td>
                    <td>{cell.mk_p === null ? "" : formatPValue(cell.mk_p)}</td>
                    <td>{cell.significant ? "Yes" : "No"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <h3>Data</h3>
        <ul className="plain-list">
          {trendMap.sources.map((source, index) => (
            <li key={index}>
              {source.name}, version {source.version}, accessed {source.accessed}.
            </li>
          ))}
        </ul>
        <p>{POWER_ACKNOWLEDGEMENT}</p>

        <WordsUsedHere variable={variable} />
      </details>
    </section>
  );
}

interface MapSettingsProps {
  draft: MapDraft;
  error: string | null;
  variables: RequestState<VariableSummary[]>;
  onChange: (draft: MapDraft) => void;
  onSubmit: () => void;
}

const BOX_FIELDS: readonly { side: keyof Box; label: string }[] = [
  { side: "north", label: "North edge" },
  { side: "south", label: "South edge" },
  { side: "west", label: "West edge" },
  { side: "east", label: "East edge" },
];

/** What the map tests, and the box it covers; every part can be changed (spec 3). */
function MapSettings({ draft, error, variables, onChange, onSubmit }: MapSettingsProps): JSX.Element {
  const list = variables.status === "done" ? variables.value : [];
  const themes = [...new Set(list.map((variable) => variable.theme))];
  const setBox = (side: keyof Box, text: string): void => {
    const box: BoxText = { ...draft.box, [side]: text };
    onChange({ ...draft, box });
  };
  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <section className="panel case-settings" aria-labelledby="map-settings-heading">
      <h2 id="map-settings-heading">Map settings</h2>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="map-variable" className="field-label">
            Variable
          </label>
          <select
            id="map-variable"
            value={draft.variable ?? ""}
            disabled={variables.status !== "done"}
            onChange={(event) => onChange({ ...draft, variable: event.target.value })}
          >
            {draft.variable === null ? <option value="">Choose a variable</option> : null}
            {themes.map((theme) => (
              <optgroup key={theme} label={theme.charAt(0).toUpperCase() + theme.slice(1)}>
                {list
                  .filter((variable) => variable.theme === theme)
                  .map((variable) => (
                    <option key={variable.id} value={variable.id}>
                      {variable.name}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
          {variables.status === "failed" ? (
            <p className="field-error">The variables could not be loaded. {variables.error.message}</p>
          ) : null}
        </div>

        <fieldset className="field">
          <legend className="field-label">Period</legend>
          <div className="field-row">
            <label className="year-field">
              <span className="field-sublabel">From</span>
              <input
                type="text"
                inputMode="numeric"
                value={draft.fromText}
                placeholder="First year"
                onChange={(event) => onChange({ ...draft, fromText: event.target.value })}
              />
            </label>
            <label className="year-field">
              <span className="field-sublabel">To</span>
              <input
                type="text"
                inputMode="numeric"
                value={draft.toText}
                placeholder="Last year"
                onChange={(event) => onChange({ ...draft, toText: event.target.value })}
              />
            </label>
          </div>
          <p className="field-hint">Both years count. Leave a box empty to use the whole record.</p>
          <p className="caution">
            <strong>Caution:</strong> {PERIOD_CAUTION}
          </p>
        </fieldset>

        <div className="field">
          <label htmlFor="map-season" className="field-label">
            Season
          </label>
          <select
            id="map-season"
            value={draft.season}
            onChange={(event) => {
              const season = event.target.value;
              if (isSeason(season)) onChange({ ...draft, season });
            }}
          >
            {SEASON_ORDER.map((season) => (
              <option key={season} value={season}>
                {SEASON_LABELS[season]}
              </option>
            ))}
          </select>
        </div>

        <fieldset className="field">
          <legend className="field-label">Box</legend>
          <div className="box-fields">
            {BOX_FIELDS.map(({ side, label }) => (
              <label key={side} className="box-field">
                <span className="field-sublabel">{label}</span>
                <input
                  type="text"
                  inputMode="decimal"
                  value={draft.box[side]}
                  onChange={(event) => setBox(side, event.target.value)}
                />
              </label>
            ))}
          </div>
          <p className="field-hint">
            In degrees: north and east are positive, south and west negative. Each side can be at most 10°.
            You can also draw a box on the globe.
          </p>
        </fieldset>

        {error !== null ? (
          <p className="field-error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="run-row">
          <button type="submit" className="button button-primary">
            Map this box
          </button>
        </div>
      </form>
    </section>
  );
}
