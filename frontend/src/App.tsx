import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { JSX } from "react";
import { getCapabilities, getCase, getExamples, getVariables, proposeCase } from "./api";
import type { ExampleCase, Investigation, VariableSummary } from "./api";
import { applyPlaceAction, caseFromDraft, draftFromCase, draftFromProposal, EMPTY_DRAFT } from "./caseDraft";
import type { CaseDraft, PlaceAction } from "./caseDraft";
import { buildCaseQuery, buildMapQuery, parseCaseQuery } from "./caseUrl";
import type { CaseParams, CasePlace } from "./caseUrl";
import type { ChatResult } from "./chat";
import { CaseActions } from "./components/CaseActions";
import type { RegionLink } from "./components/CaseActions";
import { CaseLayout } from "./components/CaseLayout";
import { CaseProblem } from "./components/CaseProblem";
import { CaseSettings } from "./components/CaseSettings";
import { CrossChecks } from "./components/CrossChecks";
import { EvidencePanel } from "./components/EvidencePanel";
import { EvidenceLesson } from "./components/EvidenceLesson";
import { ExampleCases } from "./components/ExampleCases";
import { GapChart } from "./components/GapChart";
import { GlobeStage } from "./components/GlobeStage";
import type { StageHint } from "./components/GlobeStage";
import { PeriodExplorer } from "./components/PeriodExplorer";
import { PickedPoint } from "./components/PickedPoint";
import { PlaceLegend } from "./components/PlaceLegend";
import { ProgressLine } from "./components/ProgressLine";
import { QuestionBar } from "./components/QuestionBar";
import type { AiAnswer, AiHelper } from "./components/QuestionBar";
import { PlaceOverviewView } from "./components/PlaceOverviewView";
import { RegionView } from "./components/RegionView";
import { WorldView } from "./components/WorldView";
import { SeasonsPanel } from "./components/SeasonsPanel";
import { SettingsFold } from "./components/SettingsFold";
import { ChartSkeleton, VerdictSkeleton } from "./components/Skeleton";
import { StageCaption } from "./components/StageCaption";
import { StageNote } from "./components/StageNote";
import type { PreloadedMap } from "./components/RegionView";
import { TrendChart } from "./components/TrendChart";
import { VerdictCard } from "./components/VerdictCard";
import { formatCoordinates } from "./format";
import {
  GLOBE_LOADING,
  GLOBE_UNAVAILABLE,
  GlobeContext,
  StageNoteContext,
  useGlobePlaces,
} from "./globeContext";
import type { GlobeHandle } from "./globeContext";
import type { KeywordProposal } from "./keywordMatch";
import { followInApp } from "./links";
import type { MapPlace } from "./mapCell";
import { boxAroundPlace } from "./regionBox";
import type { RegionTypes } from "./regionTypes";
import {
  casePageUrl,
  HOME_PATH,
  mapPageUrl,
  placePageUrl,
  parseRoute,
  sameCase,
  withRequestedPeriod,
  worldPageUrl,
} from "./route";
import type { Route } from "./route";
import { useRegionTypes } from "./useRegionTypes";
import { useRequest } from "./useRequest";
import type { RequestState } from "./useRequest";

const GlobeCanvas = lazy(() => import("./components/GlobeCanvas"));

const APP_NAME = "Trend Detective";

// What the globe does on each screen, shown on the stage (spec 3, "The globe").
const PICK_HINT: StageHint = {
  pointer: "Drag to turn the Earth. Click it to pick a point.",
  touch: "Turn with two fingers. Tap to pick a point.",
};
// On the first screen, while the example cases are pinned to the globe.
const EXAMPLES_HINT: StageHint = {
  pointer: "Click a pin to open an example, or pick a point.",
  touch: "Tap a pin to open it. Turn with two fingers.",
};
const REGION_HINT: StageHint = {
  pointer: "Click a cell to open it as a case.",
  touch: "Tap a cell to open it. Move with two fingers.",
};

// The heading of the case settings (CaseSettings), which the first screen's manual way in jumps to.
const SETTINGS_HEADING_ID = "settings-heading";

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
  // Counts the times the screen moved on from the last question, for the question bar.
  const [screenChanges, setScreenChanges] = useState(0);
  const settingsHeadingRef = useRef<HTMLHeadingElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLElement>(null);
  // Where a view draws its caption or key on the stage; a state, so the view draws once it exists.
  const [stageNote, setStageNote] = useState<HTMLElement | null>(null);
  const [globeHandle, setGlobeHandle] = useState<GlobeHandle | null>(null);
  const [globeUnavailable, setGlobeUnavailable] = useState(false);
  const globe = useMemo(() => {
    if (globeUnavailable) return GLOBE_UNAVAILABLE;
    return globeHandle === null ? GLOBE_LOADING : { handle: globeHandle, status: "ready" as const };
  }, [globeHandle, globeUnavailable]);
  const markGlobeUnavailable = useCallback(() => setGlobeUnavailable(true), []);
  const [aiWorking, setAiWorking] = useState(false);
  const [plannerNotices, setPlannerNotices] = useState<string[]>([]);
  const plannerController = useRef<AbortController | null>(null);
  // Spec 8, "When the AI is off": after a failure the question bar matches keywords; this holds
  // the server's reason until the user tries the AI again or starts a new conversation.
  const [aiFailure, setAiFailure] = useState<string | null>(null);
  // The last case or map the AI ran, so its page opens without asking the API again.
  const chatResult: ChatResult | null = null;

  const variables = useRequest("variables", (signal) => getVariables(undefined, undefined, signal));
  const examples = useRequest("examples", (signal) => getExamples(signal));
  // Spec 8: the question bar offers the AI only once the server says the planner is available,
  // so it never asks an AI that is off.
  const capabilities = useRequest("capabilities", (signal) => getCapabilities(signal));
  const catalogue = variables.state.status === "done" ? variables.state.value : NO_VARIABLES;
  const regionTypes = useRegionTypes(route.kind === "case" ? route.params.places : NO_PLACES);

  useEffect(() => {
    const showAddress = (): void => {
      setRoute(currentRoute());
      setPendingDraft(null);
      setPickedPoint(null);
      setScreenChanges((count) => count + 1);
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
    setScreenChanges((count) => count + 1);
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

  const showSettingsPage = (): void => {
    if (route.kind === "map" || route.kind === "place" || route.kind === "world") navigate(HOME_PATH);
  };

  const askAi = async (question: string): Promise<AiAnswer> => {
    const controller = new AbortController();
    plannerController.current = controller;
    setAiWorking(true);
    try {
      const proposal = await proposeCase(question, controller.signal);
      showSettingsPage();
      setPendingDraft({
        variable: proposal.variables[0]?.id ?? null,
        places: proposal.places,
        from: proposal.from ?? undefined,
        to: proposal.to ?? undefined,
        season: proposal.season,
      });
      setPlannerNotices(proposal.notices);
      setSettingsFocusRequest((count) => count + 1);
      return "answered";
    } catch (error) {
      if (controller.signal.aborted) return "ended";
      setAiFailure(error instanceof Error ? error.message : "AI planning is unavailable.");
      return "fall_back";
    } finally {
      setAiWorking(false);
    }
  };
  const ai: AiHelper | undefined =
    aiFailure === null &&
    capabilities.state.status === "done" &&
    capabilities.state.value.ai_planner_available
      ? { ask: askAi, working: aiWorking, onStop: () => plannerController.current?.abort(), followUp: false }
      : undefined;
  const notes =
    plannerNotices.length > 0 ? (
      <section className="panel" aria-label="AI proposal">
        <h2>Proposed settings ? Written with AI</h2>
        <ul>
          {plannerNotices.map((notice, index) => (
            <li key={index}>{notice}</li>
          ))}
        </ul>
      </section>
    ) : null;

  const handleProposal = (proposal: KeywordProposal): void => {
    const base = pendingDraft ?? (route.kind === "case" ? draftFromCase(route.params) : EMPTY_DRAFT);
    showSettingsPage();
    regionTypes.remember(proposal.places);
    setPendingDraft(draftFromProposal(base, proposal));
    setSettingsFocusRequest((count) => count + 1);
  };

  // The case settings as they stand: of the open case, or waiting for "Run this case". Every
  // change waits for "Run this case", so a case only runs once the user confirms it (spec 3).
  const openParams = route.kind === "case" ? route.params : null;
  const draft = pendingDraft ?? (openParams === null ? EMPTY_DRAFT : draftFromCase(openParams));
  const settingsPending = openParams === null || pendingDraft !== null;
  const cancelPending = (): void => {
    setPendingDraft(null);
    setScreenChanges((count) => count + 1);
  };
  const settings = (
    <CaseSettings
      draft={draft}
      variables={variables.state}
      pending={settingsPending}
      onPickCandidate={(candidate) => regionTypes.remember([candidate])}
      onChange={setPendingDraft}
      onRun={() => {
        const params = caseFromDraft(draft);
        if (params !== null) openPage(casePageUrl(params));
      }}
      onCancel={openParams !== null && pendingDraft !== null ? cancelPending : undefined}
      headingRef={settingsHeadingRef}
    />
  );

  // The picked point's buttons leave the page once one is pressed, so focus moves on to the
  // settings, where the point waits for "Run this case".
  const choosePickedPoint = (action: PlaceAction, place: CasePlace): void => {
    showSettingsPage();
    setPendingDraft(applyPlaceAction(draft, action, place));
    setPickedPoint(null);
    setSettingsFocusRequest((count) => count + 1);
  };
  const dismissPickedPoint = (): void => {
    setPickedPoint(null);
    stageRef.current?.focus({ preventScroll: true });
  };

  return (
    <GlobeContext value={globe}>
      <StageNoteContext value={stageNote}>
        <div className="app">
          <div className="site-top">
            <header className="site-header">
              <BrandMark />
              <div className="site-name">
                <h1 className="site-title">
                  <a href={HOME_PATH} onClick={(event) => followInApp(event, HOME_PATH, openPage)}>
                    {APP_NAME}
                  </a>
                </h1>
                <p className="site-tagline">Test a claim about the Earth against NASA data.</p>
              </div>
            </header>
            <QuestionBar
              onProposal={handleProposal}
              ai={ai}
              aiNotice={aiFailure === null ? null : { message: aiFailure, onRetry: () => setAiFailure(null) }}
              firstScreen={route.kind === "home" || route.kind === "bad_link"}
              screenChanges={screenChanges}
            />
          </div>
          <main id="main" className="site-main" ref={mainRef} tabIndex={-1}>
            {route.kind === "case" ? (
              <CaseView
                params={route.params}
                settings={settings}
                settingsNeeded={pendingDraft !== null}
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
            {route.kind === "place" ? (
              <PlaceOverviewView
                params={route.params}
                pickedPoint={pickedPoint}
                onOpenPage={openPage}
                onPick={setPickedPoint}
              />
            ) : null}
            {route.kind === "world" ? (
              <WorldView params={route.params} pickedPoint={pickedPoint} onPick={setPickedPoint} />
            ) : null}
            {route.kind === "home" || route.kind === "bad_link" ? (
              <StartView
                badLinkReason={route.kind === "bad_link" ? route.reason : null}
                settings={settings}
                draftPlaces={draft.places}
                pickedPoint={pickedPoint}
                examples={examples.state}
                notes={notes}
                onOpenPage={openPage}
                onPick={setPickedPoint}
              />
            ) : null}
          </main>
          <GlobeStage
            stageRef={stageRef}
            hint={stageHint(route, examples.state)}
            pick={
              pickedPoint === null ? null : (
                <PickedPoint
                  point={pickedPoint}
                  places={draft.places}
                  onChoose={choosePickedPoint}
                  onDismiss={dismissPickedPoint}
                  overviewUrl={placePageUrl({ place: pickedPoint, season: "annual" })}
                  onOpenPage={openPage}
                />
              )
            }
            noteRef={setStageNote}
          >
            <Suspense fallback={null}>
              <GlobeCanvas
                stageRef={stageRef}
                onReady={setGlobeHandle}
                onUnavailable={markGlobeUnavailable}
              />
            </Suspense>
          </GlobeStage>
          <footer className="site-footer">
            <p>
              Data: <a href="https://power.larc.nasa.gov/">NASA POWER</a> (MERRA-2 and other NASA sources).
              Globe: <a href="https://openfreemap.org">OpenFreeMap</a> tiles, ©{" "}
              <a href="https://www.openmaptiles.org/">OpenMapTiles</a>, with data from{" "}
              <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors and relief from{" "}
              <a href="https://www.naturalearthdata.com/">Natural Earth</a>. Place names:{" "}
              <a href="https://www.geonames.org/">GeoNames</a> (CC BY 4.0).
            </p>
          </footer>
        </div>
      </StageNoteContext>
    </GlobeContext>
  );
}

/** The app's own mark: a magnifying glass with the Earth in its lens. */
function BrandMark(): JSX.Element {
  return (
    <svg
      className="brand-mark"
      viewBox="0 0 40 40"
      width="40"
      height="40"
      aria-hidden="true"
      focusable="false"
    >
      <circle className="brand-lens" cx="17" cy="17" r="12" />
      <g className="brand-lines">
        <ellipse cx="17" cy="17" rx="5" ry="12" />
        <path d="M5 17h24M7.5 10.5h19M7.5 23.5h19" />
      </g>
      <path className="brand-handle" d="M26.5 26.5l9 9" />
    </svg>
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
  const mapPlaces = useMemo(() => placesOfDraft(props.draftPlaces), [props.draftPlaces]);
  useGlobePlaces(mapPlaces, props.pickedPoint, props.onPick);
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
      <p className="home-manual">
        Or <a href={`#${SETTINGS_HEADING_ID}`}>set up a case by hand</a>: choose the variable, the place and
        the period yourself.
      </p>
      <section className="home-section" aria-labelledby="examples-heading">
        <h2 id="examples-heading">Example cases</h2>
        <p className="panel-intro">
          Each one tests a claim about the Earth. Open one to see how a case works.
        </p>
        <ExampleCases examples={props.examples} onOpen={props.onOpenPage} onGlobe />
      </section>
      <div className="case-layout">
        <div className="case-side">{props.settings}</div>
        <div className="case-main">
          <PlaceLegend places={mapPlaces} pickedPoint={props.pickedPoint} />
        </div>
      </div>
    </>
  );
}

interface CaseViewProps {
  params: CaseParams;
  settings: JSX.Element;
  /** True while settings wait for "Run this case", so they are shown unfolded. */
  settingsNeeded: boolean;
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
 * An open case: the verdict, its chart, what to do with the answer, the variables to test next,
 * the key to the globe, the period explorer and the evidence.
 */
function CaseView(props: CaseViewProps): JSX.Element {
  const { params, preloaded } = props;
  const key = buildCaseQuery(params);
  const request = useRequest(key, (signal) => loadCase(params, key, preloaded, signal), {
    answerKey: (investigation) => buildCaseQuery(pinnedCase(params, investigation)),
    onDone: (investigation) => {
      const normalised = pinnedCase(params, investigation);
      if (!sameCase(normalised, params)) props.onNormalised(normalised);
    },
  });
  const { state } = request;
  const investigation = shownInvestigation(state);
  const loading = state.status === "loading";
  const shown = state.status === "failed" ? null : investigation;
  const firstLoad = loading && shown === null;
  const resultsClass = loading ? "case-results is-stale" : "case-results";
  // The globe turns to the places as soon as the case opens; their grid cells follow the answer.
  const mapPlaces = useMemo(
    () => (state.status === "done" ? placesOnMap(state.value) : placesOfDraft(params.places)),
    [state, params.places],
  );
  useGlobePlaces(mapPlaces, props.pickedPoint, props.onPick);

  useEffect(() => {
    document.title = investigation === null ? APP_NAME : `${caseTitle(investigation)} · ${APP_NAME}`;
    return () => {
      document.title = APP_NAME;
    };
  }, [investigation]);

  return (
    <CaseLayout
      side={
        <SettingsFold
          label="Change this case"
          hint="Variable, places, period and season"
          needed={props.settingsNeeded || state.status === "failed"}
        >
          {props.settings}
        </SettingsFold>
      }
      answer={
        <>
          <ProgressLine active={loading} label="Getting the data and testing the trend…" />
          {firstLoad ? <VerdictSkeleton /> : null}
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
          {/* The chart follows the verdict at once: the proof beside the answer. It stays out of
              the live region, whose text is read aloud when it changes. */}
          {shown !== null ? (
            <div className={resultsClass} aria-busy={loading}>
              <TrendChart investigation={shown} />
            </div>
          ) : firstLoad ? (
            <ChartSkeleton />
          ) : null}
          {shown !== null ? (
            <>
              {!loading ? (
                <CaseActions
                  key={key}
                  subject="case"
                  region={regionLink(params, props.onOpenPage)}
                  overview={overviewLink(params, props.onOpenPage)}
                  world={worldLink(params, props.catalogue, props.onOpenPage)}
                />
              ) : null}
              <StageNote>
                <StageCaption investigation={shown} />
              </StageNote>
            </>
          ) : null}
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
            <PlaceLegend places={mapPlaces} pickedPoint={props.pickedPoint} />
            <PeriodExplorer params={params} investigation={shown} onOpenCase={props.onOpenCase} />
            <GapChart investigation={shown} />
            <SeasonsPanel params={params} investigation={shown} onOpenPage={props.onOpenPage} />
            <EvidencePanel investigation={shown} />
            <EvidenceLesson />
          </div>
        ) : null
      }
    />
  );
}

function pinnedCase(params: CaseParams, investigation: Investigation): CaseParams {
  const query = investigation.app_url.split("?")[1];
  const parsed = query === undefined ? null : parseCaseQuery(query);
  return parsed?.ok ? parsed.value : withRequestedPeriod(params, investigation.requested);
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

/** "The whole world": the case's variable, period and season in the world sample, when it covers it. */
function worldLink(
  params: CaseParams,
  catalogue: readonly VariableSummary[],
  onOpenPage: (url: string) => void,
): RegionLink | undefined {
  const variable = catalogue.find((item) => item.id === params.variable);
  if (variable?.world_mean !== true) return undefined;
  const url = worldPageUrl({
    variable: params.variable,
    from: params.from,
    to: params.to,
    season: params.season,
  });
  return { url, placeName: "the whole world", onOpenPage };
}

/** "What is changing here?": every variable at the case's first place, over the case's period. */
function overviewLink(params: CaseParams, onOpenPage: (url: string) => void): RegionLink | undefined {
  const [first] = params.places;
  if (first === undefined) return undefined;
  const url = placePageUrl({ place: first, from: params.from, to: params.to, season: params.season });
  return { url, placeName: first.name ?? formatCoordinates(first.lat, first.lon), onOpenPage };
}

function shownInvestigation(state: RequestState<Investigation>): Investigation | null {
  if (state.status === "done") return state.value;
  if (state.status === "loading") return state.stale;
  return null;
}

/** The line on the stage that says what the globe does on this screen (spec 3, "The globe"). */
function stageHint(route: Route, examples: RequestState<ExampleCase[]>): StageHint {
  if (route.kind === "map") return REGION_HINT;
  const pinned = examples.status === "done" && examples.value.length > 0;
  return (route.kind === "home" || route.kind === "bad_link") && pinned ? EXAMPLES_HINT : PICK_HINT;
}

/** The places of a case that has not run: their points and names, without grid cells. */
function placesOfDraft(places: readonly CasePlace[]): MapPlace[] {
  return places.map((place) => ({
    name: place.name ?? formatCoordinates(place.lat, place.lon),
    lat: place.lat,
    lon: place.lon,
  }));
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
