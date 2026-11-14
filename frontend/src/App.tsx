import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { JSX } from "react";
import { getCase, getExamples, getVariables } from "./api";
import type { ExampleCase, Investigation, VariableSummary } from "./api";
import { caseFromDraft, draftFromCase, draftFromProposal, EMPTY_DRAFT } from "./caseDraft";
import type { CaseDraft } from "./caseDraft";
import { buildCaseQuery, buildMapQuery } from "./caseUrl";
import type { CaseParams, CasePlace } from "./caseUrl";
import type { ChatResult } from "./chat";
import { CaseLayout } from "./components/CaseLayout";
import { CaseProblem } from "./components/CaseProblem";
import { CaseSettings } from "./components/CaseSettings";
import { CrossChecks } from "./components/CrossChecks";
import { DetectiveNotes } from "./components/DetectiveNotes";
import { EvidencePanel } from "./components/EvidencePanel";
import { ExampleCases } from "./components/ExampleCases";
import type { MapPlace } from "./components/PlaceMap";
import { PeriodExplorer } from "./components/PeriodExplorer";
import { ProgressLine } from "./components/ProgressLine";
import { QuestionBar } from "./components/QuestionBar";
import type { AiAnswer, AiHelper } from "./components/QuestionBar";
import { RegionView } from "./components/RegionView";
import type { PreloadedMap } from "./components/RegionView";
import { TrendChart } from "./components/TrendChart";
import { VerdictCard } from "./components/VerdictCard";
import { formatCoordinates } from "./format";
import type { KeywordProposal } from "./keywordMatch";
import { followInApp } from "./links";
import { boxAroundPlace } from "./regionBox";
import type { RegionTypes } from "./regionTypes";
import { casePageUrl, HOME_PATH, mapPageUrl, parseRoute, sameCase, withRequestedPeriod } from "./route";
import type { Route } from "./route";
import { useChat } from "./useChat";
import { useRegionTypes } from "./useRegionTypes";
import { useRequest } from "./useRequest";
import type { RequestState } from "./useRequest";

const PlaceMap = lazy(() => import("./components/PlaceMap"));

const APP_NAME = "Trend Detective";

const NO_PLACES: readonly CasePlace[] = [];
const NO_VARIABLES: readonly VariableSummary[] = [];

function currentRoute(): Route {
  return parseRoute(window.location.pathname, window.location.search);
}

/** A case that is already in hand, such as one the AI ran, keyed by its parameter string. */
interface PreloadedCase {
  key: string;
  investigation: Investigation;
}

/** The one screen of the app; the address bar decides what it shows (spec 3 and spec 10). */
export default function App(): JSX.Element {
  const [route, setRoute] = useState<Route>(currentRoute);
  // Settings that wait for "Run this case": a keyword match, or a case set up by hand.
  const [pendingDraft, setPendingDraft] = useState<CaseDraft | null>(null);
  const [pickedPoint, setPickedPoint] = useState<CasePlace | null>(null);
  const [settingsFocusRequest, setSettingsFocusRequest] = useState(0);
  const [mainFocusRequest, setMainFocusRequest] = useState(0);
  const settingsHeadingRef = useRef<HTMLHeadingElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const chat = useChat();
  // Spec 8, "When the AI is off": after a failure the question bar matches keywords; this holds
  // the server's reason until the user tries the AI again or starts a new conversation.
  const [aiFailure, setAiFailure] = useState<string | null>(null);
  // The last case or map the AI ran, so its page opens without asking the API again.
  const [chatResult, setChatResult] = useState<ChatResult | null>(null);

  const variables = useRequest("variables", (signal) => getVariables(undefined, undefined, signal));
  const examples = useRequest("examples", (signal) => getExamples(signal));
  const catalogue = variables.state.status === "done" ? variables.state.value : NO_VARIABLES;
  const regionTypes = useRegionTypes(route.kind === "case" ? route.params.places : NO_PLACES);

  useEffect(() => {
    const showAddress = (): void => {
      setRoute(currentRoute());
      setPendingDraft(null);
      setPickedPoint(null);
    };
    window.addEventListener("popstate", showAddress);
    return () => window.removeEventListener("popstate", showAddress);
  }, []);

  useEffect(() => {
    if (settingsFocusRequest > 0) settingsHeadingRef.current?.focus();
  }, [settingsFocusRequest]);

  // The control that opened a page may leave with the old view, so focus moves to the start of
  // the new page instead of falling back to the document.
  useEffect(() => {
    if (mainFocusRequest > 0) mainRef.current?.focus({ preventScroll: true });
  }, [mainFocusRequest]);

  const navigate = (url: string): void => {
    // Opening the page already shown, as when the AI reruns the case on screen, adds no history entry.
    const shownUrl = `${window.location.pathname}${window.location.search}`;
    if (url !== shownUrl) window.history.pushState(null, "", url);
    setRoute(currentRoute());
    setPendingDraft(null);
    setPickedPoint(null);
  };
  const openCase = (params: CaseParams): void => navigate(casePageUrl(params));
  const openPage = (url: string): void => {
    navigate(url);
    window.scrollTo(0, 0);
    setMainFocusRequest((count) => count + 1);
  };
  // Spec 10: the API fills in the period, and the address bar then holds the full case.
  const showNormalisedCase = (params: CaseParams): void => {
    window.history.replaceState(null, "", casePageUrl(params));
    setRoute({ kind: "case", params });
  };
  const showNormalisedPage = (url: string): void => {
    window.history.replaceState(null, "", url);
    setRoute(currentRoute());
  };

  // Spec 8: a case or map the AI ran opens exactly as one set by hand, and the address follows.
  const showChatResult = (result: ChatResult): void => {
    setChatResult(result);
    navigate(result.url);
  };
  const askAi = async (question: string): Promise<AiAnswer> => {
    const caseQuery = route.kind === "case" ? buildCaseQuery(route.params) : undefined;
    const outcome = await chat.ask(question, caseQuery, showChatResult);
    if (outcome.kind === "answered") return "answered";
    if (outcome.kind === "stopped") return "ended";
    setAiFailure(outcome.message);
    return outcome.showedResult ? "ended" : "fall_back";
  };
  const startNewConversation = (): void => {
    chat.reset();
    setAiFailure(null);
  };
  const ai: AiHelper | undefined =
    aiFailure === null
      ? { ask: askAi, working: chat.running, onStop: chat.stop, followUp: chat.state.turns.length > 0 }
      : undefined;
  const notes =
    chat.state.turns.length > 0 ? (
      <DetectiveNotes
        turns={chat.state.turns}
        onNewConversation={startNewConversation}
        onOpenPage={openPage}
      />
    ) : null;

  const handleProposal = (proposal: KeywordProposal): void => {
    const base = pendingDraft ?? (route.kind === "case" ? draftFromCase(route.params) : EMPTY_DRAFT);
    if (route.kind === "map") navigate(HOME_PATH);
    regionTypes.remember(proposal.places);
    setPendingDraft(draftFromProposal(base, proposal));
    setSettingsFocusRequest((count) => count + 1);
  };

  const settingsFor = (openParams: CaseParams | null): JSX.Element => {
    const draft = pendingDraft ?? (openParams === null ? EMPTY_DRAFT : draftFromCase(openParams));
    const pending = openParams === null || pendingDraft !== null;
    const applyLive = (next: CaseDraft): void => {
      const params = caseFromDraft(next);
      if (params === null) setPendingDraft(next);
      else openCase(params);
    };
    return (
      <CaseSettings
        draft={draft}
        variables={variables.state}
        pending={pending}
        pickedPoint={pickedPoint}
        onDismissPickedPoint={() => setPickedPoint(null)}
        onPickCandidate={(candidate) => regionTypes.remember([candidate])}
        onChange={pending ? setPendingDraft : applyLive}
        onRun={() => {
          const params = caseFromDraft(draft);
          if (params !== null) openPage(casePageUrl(params));
        }}
        onCancel={openParams !== null && pendingDraft !== null ? () => setPendingDraft(null) : undefined}
        headingRef={settingsHeadingRef}
      />
    );
  };

  return (
    <div className="app">
      <header className="site-header">
        <h1 className="site-title">
          <a href={HOME_PATH} onClick={(event) => followInApp(event, HOME_PATH, openPage)}>
            {APP_NAME}
          </a>
        </h1>
        <p className="site-tagline">Test a claim about the Earth against NASA data.</p>
      </header>
      <QuestionBar
        onProposal={handleProposal}
        ai={ai}
        aiNotice={aiFailure === null ? null : { message: aiFailure, onRetry: () => setAiFailure(null) }}
        showPrompts={route.kind !== "case"}
      />
      <main id="main" className="site-main" ref={mainRef} tabIndex={-1}>
        {route.kind === "case" ? (
          <CaseView
            params={route.params}
            settings={settingsFor(route.params)}
            pickedPoint={pickedPoint}
            examples={examples.state}
            preloaded={preloadedCase(chatResult)}
            notes={notes}
            catalogue={catalogue}
            regionTypes={regionTypes.known}
            onOpenCase={openCase}
            onOpenPage={openPage}
            onNormalised={showNormalisedCase}
            onPick={setPickedPoint}
          />
        ) : null}
        {route.kind === "map" ? (
          <RegionView
            query={route.query}
            variables={variables.state}
            examples={examples.state}
            preloaded={preloadedMap(chatResult)}
            notes={notes}
            onOpenPage={openPage}
            onShowMap={navigate}
            onNormalised={showNormalisedPage}
          />
        ) : null}
        {route.kind === "home" || route.kind === "bad_link" ? (
          <StartView
            badLinkReason={route.kind === "bad_link" ? route.reason : null}
            settings={settingsFor(null)}
            draftPlaces={(pendingDraft ?? EMPTY_DRAFT).places}
            pickedPoint={pickedPoint}
            examples={examples.state}
            notes={notes}
            onOpenPage={openPage}
            onPick={setPickedPoint}
          />
        ) : null}
      </main>
      <footer className="site-footer">
        <p>
          Data: <a href="https://power.larc.nasa.gov/">NASA POWER</a> (MERRA-2 and other NASA sources). Map
          tiles: © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>. Place
          names: <a href="https://www.geonames.org/">GeoNames</a> (CC BY 4.0).
        </p>
      </footer>
    </div>
  );
}

function preloadedCase(result: ChatResult | null): PreloadedCase | null {
  if (result?.kind !== "case") return null;
  return { key: buildCaseQuery(result.params), investigation: result.investigation };
}

function preloadedMap(result: ChatResult | null): PreloadedMap | null {
  if (result?.kind !== "map") return null;
  return { key: buildMapQuery(result.params), map: result.map };
}

interface StartViewProps {
  badLinkReason: string | null;
  settings: JSX.Element;
  draftPlaces: readonly CasePlace[];
  pickedPoint: CasePlace | null;
  examples: RequestState<ExampleCase[]>;
  /** The AI's notes, when a conversation is going. */
  notes: JSX.Element | null;
  onOpenPage: (url: string) => void;
  onPick: (point: CasePlace) => void;
}

/** The first screen: example cases, and a case set up by hand. Never an empty chart (spec 3). */
function StartView(props: StartViewProps): JSX.Element {
  const mapPlaces = useMemo(
    () =>
      props.draftPlaces.map((place): MapPlace => ({
        name: place.name ?? formatCoordinates(place.lat, place.lon),
        lat: place.lat,
        lon: place.lon,
      })),
    [props.draftPlaces],
  );
  return (
    <>
      {props.badLinkReason !== null ? (
        <div className="notice notice-error" role="alert">
          <h2>This link does not open a case</h2>
          <p>{props.badLinkReason}</p>
          <p>Open an example case, or set up a case below.</p>
        </div>
      ) : null}
      {props.notes}
      <section className="home-section" aria-labelledby="examples-heading">
        <h2 id="examples-heading">Example cases</h2>
        <p className="panel-intro">
          Each one tests a claim about the Earth. Open one to see how a case works.
        </p>
        <ExampleCases examples={props.examples} onOpen={props.onOpenPage} />
      </section>
      <div className="case-layout">
        <div className="case-side">{props.settings}</div>
        <div className="case-main">
          <MapPanel places={mapPlaces} pickedPoint={props.pickedPoint} onPick={props.onPick} />
        </div>
      </div>
    </>
  );
}

interface CaseViewProps {
  params: CaseParams;
  settings: JSX.Element;
  pickedPoint: CasePlace | null;
  examples: RequestState<ExampleCase[]>;
  preloaded: PreloadedCase | null;
  /** The AI's notes, when a conversation is going. */
  notes: JSX.Element | null;
  /** The catalogue, empty until it loads. */
  catalogue: readonly VariableSummary[];
  regionTypes: RegionTypes;
  onOpenCase: (params: CaseParams) => void;
  onOpenPage: (url: string) => void;
  onNormalised: (params: CaseParams) => void;
  onPick: (point: CasePlace) => void;
}

/**
 * An open case: the verdict, the variables to test next, the chart, the map, the period explorer
 * and the evidence.
 */
function CaseView(props: CaseViewProps): JSX.Element {
  const { params, preloaded } = props;
  const key = buildCaseQuery(params);
  const request = useRequest(key, (signal) => loadCase(params, key, preloaded, signal), {
    answerKey: (investigation) => buildCaseQuery(withRequestedPeriod(params, investigation.requested)),
    onDone: (investigation) => {
      const normalised = withRequestedPeriod(params, investigation.requested);
      if (!sameCase(normalised, params)) props.onNormalised(normalised);
    },
  });
  const { state } = request;
  const investigation = shownInvestigation(state);
  const loading = state.status === "loading";
  const shown = state.status === "failed" ? null : investigation;
  const resultsClass = loading ? "case-results is-stale" : "case-results";
  const mapPlaces = useMemo(
    () => (investigation === null ? [] : placesOnMap(investigation)),
    [investigation],
  );

  useEffect(() => {
    document.title = investigation === null ? APP_NAME : `${caseTitle(investigation)} · ${APP_NAME}`;
    return () => {
      document.title = APP_NAME;
    };
  }, [investigation]);

  return (
    <CaseLayout
      side={props.settings}
      answer={
        <>
          <ProgressLine active={loading} label="Getting the data and testing the trend…" />
          {state.status === "failed" ? (
            <CaseProblem
              error={state.error}
              onRetry={request.retry}
              examples={props.examples}
              onOpenExample={props.onOpenPage}
            />
          ) : null}
          {/* In the page while empty, so screen readers announce the verdict when it arrives. */}
          <div className="live-region" aria-live="polite">
            {shown !== null ? (
              <div className={resultsClass} aria-busy={loading}>
                <VerdictCard investigation={shown} />
              </div>
            ) : null}
          </div>
          {props.notes}
          {shown !== null ? (
            <CrossChecks
              params={params}
              variables={props.catalogue}
              regionTypes={props.regionTypes}
              onOpenPage={props.onOpenPage}
            />
          ) : null}
        </>
      }
      main={
        shown !== null ? (
          <div className={resultsClass} aria-busy={loading}>
            <TrendChart investigation={shown} />
            <MapPanel
              places={mapPlaces}
              pickedPoint={props.pickedPoint}
              onPick={props.onPick}
              region={regionLink(params, props.onOpenPage)}
            />
            <PeriodExplorer params={params} investigation={shown} onOpenCase={props.onOpenCase} />
            <EvidencePanel investigation={shown} />
          </div>
        ) : null
      }
    />
  );
}

function loadCase(
  params: CaseParams,
  key: string,
  preloaded: PreloadedCase | null,
  signal: AbortSignal,
): Promise<Investigation> {
  if (preloaded?.key === key) return Promise.resolve(preloaded.investigation);
  return getCase(params, signal);
}

interface RegionLink {
  url: string;
  placeName: string;
  onOpenPage: (url: string) => void;
}

/** "Map this region": the case's variable, period and season over a box around its first place. */
function regionLink(params: CaseParams, onOpenPage: (url: string) => void): RegionLink | undefined {
  const [first] = params.places;
  if (first === undefined) return undefined;
  const url = mapPageUrl({
    variable: params.variable,
    from: params.from,
    to: params.to,
    season: params.season,
    box: boxAroundPlace(first),
  });
  return { url, placeName: first.name ?? formatCoordinates(first.lat, first.lon), onOpenPage };
}

function shownInvestigation(state: RequestState<Investigation>): Investigation | null {
  if (state.status === "done") return state.value;
  if (state.status === "loading") return state.stale;
  return null;
}

function placesOnMap(investigation: Investigation): MapPlace[] {
  return investigation.results.map(({ place }) => ({
    name: place.name,
    lat: place.lat,
    lon: place.lon,
    cell: place.cell,
  }));
}

function caseTitle(investigation: Investigation): string {
  const names = investigation.results.map((result) => result.place.name).join(", ");
  return `${investigation.variable.name} in ${names}`;
}

function MapPanel({
  places,
  pickedPoint,
  onPick,
  region,
}: {
  places: readonly MapPlace[];
  pickedPoint: CasePlace | null;
  onPick: (point: CasePlace) => void;
  region?: RegionLink;
}): JSX.Element {
  return (
    <>
      <Suspense fallback={<div className="panel map-placeholder">Loading the map…</div>}>
        <PlaceMap places={places} onPick={onPick} />
      </Suspense>
      {region !== undefined ? (
        <p className="region-link">
          <a
            className="button button-secondary"
            href={region.url}
            onClick={(event) => followInApp(event, region.url, region.onOpenPage)}
          >
            Map this region
          </a>{" "}
          <span className="field-hint">
            The same test in every grid cell of a 10° by 10° box around {region.placeName}.
          </span>
        </p>
      ) : null}
      <p className="status-text" role="status">
        {pickedPoint === null
          ? ""
          : `You picked ${formatCoordinates(pickedPoint.lat, pickedPoint.lon)}. Choose what to do with it in the case settings.`}
      </p>
    </>
  );
}
