import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { JSX } from "react";
import { discover, explain, getCapabilities, getCase, getExamples, getVariables, proposeCase } from "./api";
import type { ExampleCase, Investigation, Proposal, VariableSummary } from "./api";
import {
  applyPlaceAction,
  caseFromDraft,
  draftFromCase,
  draftFromProposal,
  EMPTY_DRAFT,
  missingSetting,
  questionIsReady,
  readySummary,
} from "./caseDraft";
import type { CaseDraft, MissingSetting, PlaceAction } from "./caseDraft";
import { buildCaseQuery, buildMapQuery, parseCaseQuery } from "./caseUrl";
import type { CaseParams, CasePlace } from "./caseUrl";
import type { ChatResult } from "./chat";
import { AskPanel } from "./components/AskPanel";
import type { Explain } from "./components/AskPanel";
import { CopyLink, ExploreFurther } from "./components/CaseActions";
import type { RegionLink } from "./components/CaseActions";
import { CaseLayout } from "./components/CaseLayout";
import { CaseProblem } from "./components/CaseProblem";
import { CaseSettings } from "./components/CaseSettings";
import { CaseRail } from "./components/CaseRail";
import { CaseTabs } from "./components/CaseTabs";
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
import type { AiAnswer, AiHelper, DiscoveryHelper, ReadyCase } from "./components/QuestionBar";
import { PlaceOverviewView } from "./components/PlaceOverviewView";
import { RecordYears } from "./components/RecordYears";
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
import { VerdictLine } from "./components/VerdictLine";
import {
  applyChoice,
  draftFromAiProposal,
  draftWithSuggestion,
  proposalIsReady,
  toDiscoveryDraft,
} from "./discovery";
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
import { CaseRailContext } from "./caseRailContext";
import { useRequest } from "./useRequest";
import { useScrolledPast } from "./useScrolledPast";
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

// The ids of the case settings' fields (CaseSettings, PlaceSearch), focused when one is still empty.
const SETTING_FIELD_IDS: Readonly<Record<MissingSetting, string>> = {
  variable: "variable",
  place: "place-search",
};

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
  // Focus for settings the AI left incomplete: the field still to choose, so the user lands on it.
  const [fieldFocus, setFieldFocus] = useState<{ field: MissingSetting | null; count: number }>({
    field: null,
    count: 0,
  });
  const [readyFocusRequest, setReadyFocusRequest] = useState(0);
  // True while the settings waiting for "Run this case" came from a question, so the question bar
  // offers to run them.
  const [readyFromQuestion, setReadyFromQuestion] = useState(false);
  const [mainFocusRequest, setMainFocusRequest] = useState(0);
  // Counts the times the screen moved on from the last question, for the question bar.
  const [screenChanges, setScreenChanges] = useState(0);
  const settingsHeadingRef = useRef<HTMLHeadingElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLElement>(null);
  // Where a view draws its caption or key on the stage; a state, so the view draws once it exists.
  const [stageNote, setStageNote] = useState<HTMLElement | null>(null);
  const [caseRail, setCaseRail] = useState<HTMLElement | null>(null);
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
      setReadyFromQuestion(false);
      setScreenChanges((count) => count + 1);
    };
    window.addEventListener("popstate", showAddress);
    return () => window.removeEventListener("popstate", showAddress);
  }, []);

  useEffect(() => {
    if (settingsFocusRequest > 0) settingsHeadingRef.current?.focus();
  }, [settingsFocusRequest]);

  useEffect(() => {
    if (fieldFocus.count === 0) return;
    const target =
      fieldFocus.field === null ? null : document.getElementById(SETTING_FIELD_IDS[fieldFocus.field]);
    if (target === null) {
      settingsHeadingRef.current?.focus();
      return;
    }
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: "center" });
  }, [fieldFocus]);

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
    setReadyFromQuestion(false);
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
  // The settings a question builds on: those waiting for "Run this case", or the open case's.
  const currentDraft = (): CaseDraft =>
    pendingDraft ?? (route.kind === "case" ? draftFromCase(route.params) : EMPTY_DRAFT);
  // Settings from the AI wait for "Run this case": a whole case is offered under the question,
  // and an incomplete one, when the user asked for it, sends focus to the settings.
  const fillFromAi = (next: CaseDraft, ready: boolean, focusIfIncomplete: boolean): void => {
    showSettingsPage();
    setPendingDraft(next);
    setReadyFromQuestion(ready);
    if (!focusIfIncomplete) return;
    // After the user's own choice, focus goes where the next step is: "Run this case" for a
    // whole case, otherwise the setting still to choose.
    if (ready) setReadyFocusRequest((count) => count + 1);
    else setFieldFocus((last) => ({ field: missingSetting(next), count: last.count + 1 }));
  };
  const askDiscovery: DiscoveryHelper["discover"] = async (question, choice, signal) => {
    let draft = currentDraft();
    if (choice !== null) {
      draft = applyChoice(draft, choice);
      if (choice.place != null) regionTypes.remember([choice.place]);
      fillFromAi(draft, false, false);
    }
    const response = await discover(question, toDiscoveryDraft(draft), signal);
    // A screen change cancels the question; its answer must not fill the settings of a page left.
    signal.throwIfAborted();
    const { proposal } = response;
    if (response.status === "ready" && proposal != null) {
      regionTypes.remember(proposal.places);
      const next = draftFromAiProposal(draft, proposal);
      fillFromAi(next, proposalIsReady(proposal, next), false);
    }
    return response;
  };
  const discoveryHelper: DiscoveryHelper | undefined =
    aiFailure === null &&
    capabilities.state.status === "done" &&
    capabilities.state.value.ai_discovery_available === true
      ? {
          discover: askDiscovery,
          onUseVariable: (variable, response) => {
            const { draft: next, ready } = draftWithSuggestion(currentDraft(), response, variable.id);
            fillFromAi(next, ready, true);
          },
          onManual: () => {
            showSettingsPage();
            // Pending settings show unfolded, so the heading that takes focus is on screen.
            setPendingDraft(currentDraft());
            setSettingsFocusRequest((count) => count + 1);
          },
          onFailure: setAiFailure,
        }
      : undefined;
  // Spec 8: the "Ask about this investigation" panel shows only once the server says so.
  const explanationAvailable =
    capabilities.state.status === "done" && capabilities.state.value.ai_explanation_available === true;
  const loadExplanationProposal = (proposal: Proposal): void => {
    regionTypes.remember(proposal.places);
    fillFromAi(draftFromAiProposal(currentDraft(), proposal), false, true);
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
        <h2>Proposed settings · Written with AI</h2>
        <ul>
          {plannerNotices.map((notice, index) => (
            <li key={index}>{notice}</li>
          ))}
        </ul>
      </section>
    ) : null;

  // A complete case from a question waits under the question bar, where the user is looking; an
  // incomplete one sends focus to the settings, where the missing part is filled in.
  const handleProposal = (proposal: KeywordProposal): void => {
    const base = pendingDraft ?? (route.kind === "case" ? draftFromCase(route.params) : EMPTY_DRAFT);
    showSettingsPage();
    regionTypes.remember(proposal.places);
    const next = draftFromProposal(base, proposal);
    setPendingDraft(next);
    const ready = questionIsReady(proposal, next);
    setReadyFromQuestion(ready);
    if (!ready) setSettingsFocusRequest((count) => count + 1);
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
      heading={route.kind === "home" || route.kind === "bad_link" ? "Or set it up by hand" : undefined}
    />
  );

  const readyParams = readyFromQuestion && pendingDraft !== null ? caseFromDraft(pendingDraft) : null;
  const readySummaryText = pendingDraft !== null ? readySummary(pendingDraft, catalogue) : null;
  const readyCase: ReadyCase | null =
    readyParams !== null && readySummaryText !== null
      ? {
          summary: readySummaryText,
          onRun: () => openPage(casePageUrl(readyParams)),
          onEdit: () => setSettingsFocusRequest((count) => count + 1),
          focusRequest: readyFocusRequest,
        }
      : null;

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
        <CaseRailContext value={caseRail}>
          <div className={route.kind === "home" || route.kind === "bad_link" ? "app" : "app has-answer"}>
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
                discovery={discoveryHelper}
                aiNotice={
                  aiFailure === null ? null : { message: aiFailure, onRetry: () => setAiFailure(null) }
                }
                firstScreen={route.kind === "home" || route.kind === "bad_link"}
                ready={readyCase}
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
                  ask={explanationAvailable ? { explain, onProposal: loadExplanationProposal } : undefined}
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
                  settingsNeeded={pendingDraft !== null || route.kind === "bad_link"}
                  draftPlaces={draft.places}
                  pickedPoint={pickedPoint}
                  examples={examples.state}
                  notes={notes}
                  onOpenPage={openPage}
                  onPick={setPickedPoint}
                />
              ) : null}
            </main>
            {/* The right-hand column of a results page, above the globe (spec 3): views draw into it. */}
            <div className="case-rail" ref={setCaseRail} />
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
            {route.kind === "home" || route.kind === "bad_link" ? (
              <section className="home-section home-examples" aria-labelledby="examples-heading">
                <h2 id="examples-heading">Example cases</h2>
                <p className="panel-intro">
                  Each one tests a claim about the Earth. Open one to see how a case works.
                </p>
                <ExampleCases examples={examples.state} onOpen={openPage} onGlobe />
              </section>
            ) : null}
            <footer className="site-footer">
              <p>
                Data: <a href="https://power.larc.nasa.gov/">NASA POWER</a> (MERRA-2 and other NASA sources).
                Globe: <a href="https://openfreemap.org">OpenFreeMap</a> tiles, ©{" "}
                <a href="https://www.openmaptiles.org/">OpenMapTiles</a>, with data from{" "}
                <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors and relief
                from <a href="https://www.naturalearthdata.com/">Natural Earth</a>. Place names:{" "}
                <a href="https://www.geonames.org/">GeoNames</a> (CC BY 4.0).
              </p>
            </footer>
          </div>
        </CaseRailContext>
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
  /** True while the settings hold something to check or finish, so they show unfolded. */
  settingsNeeded: boolean;
  draftPlaces: readonly CasePlace[];
  pickedPoint: CasePlace | null;
  examples: RequestState<ExampleCase[]>;
  /** The AI's notes, when a conversation is going. */
  notes: JSX.Element | null;
  onOpenPage: (url: string) => void;
  onPick: (point: CasePlace) => void;
}

/**
 * The first screen: under the question, a case set up by hand (folded until something needs
 * choosing), then the example cases and the key to the globe. Never an empty chart (spec 3).
 */
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
      {/* The settings come right after the question and its answer, beside the globe, so a
          question that leaves something to choose is finished where the user is looking. */}
      <div className="case-layout">
        <div className="case-side">{props.settings}</div>
      </div>
      <div className="case-layout">
        <div className="case-main">
          <PlaceLegend places={mapPlaces} pickedPoint={props.pickedPoint} />
        </div>
      </div>
    </>
  );
}

/** "Ask about this investigation", when the server offers explanations (spec 8). */
interface CaseAsk {
  explain: Explain;
  onProposal: (proposal: Proposal) => void;
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
  /** The panel for questions about the case; left out while explanations are unavailable. */
  ask?: CaseAsk;
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
  const verdictRef = useRef<HTMLDivElement>(null);
  const verdictScrolledPast = useScrolledPast(verdictRef);
  const cellCount = mapPlaces.filter((place) => place.cell !== undefined).length;

  useEffect(() => {
    document.title = investigation === null ? APP_NAME : `${caseTitle(investigation)} · ${APP_NAME}`;
    return () => {
      document.title = APP_NAME;
    };
  }, [investigation]);

  // "Change this case" stands beside the tabs once a case is on screen, and alone before that.
  const settingsFold = (
    <SettingsFold
      label="Change this case"
      hint="Variable, places, period and season"
      needed={props.settingsNeeded || state.status === "failed"}
    >
      {props.settings}
    </SettingsFold>
  );

  return (
    <CaseLayout
      pinned={shown !== null ? <VerdictLine investigation={shown} shown={verdictScrolledPast} /> : null}
      side={shown === null ? settingsFold : undefined}
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
          <div className="live-region" aria-live="polite" ref={verdictRef}>
            {shown !== null ? (
              <div className={resultsClass} aria-busy={loading}>
                <VerdictCard
                  investigation={shown}
                  actions={!loading ? <CopyLink key={key} subject="case" /> : undefined}
                />
              </div>
            ) : null}
          </div>
          {/* The chart follows the verdict at once, in the first tab: the proof beside the answer.
              The tabs stay out of the live region, whose text is read aloud when it changes. */}
          {shown !== null ? (
            <div className={resultsClass} aria-busy={loading}>
              <CaseTabs
                beside={settingsFold}
                panels={{
                  answer: (
                    <>
                      <TrendChart investigation={shown} />
                      <RecordYears
                        results={shown.results}
                        variable={shown.variable}
                        showNames={shown.results.length > 1}
                      />
                      {!loading && props.ask !== undefined ? (
                        <CaseRail>
                          <AskPanel
                            key={shown.id}
                            investigation={shown}
                            explain={props.ask.explain}
                            onProposal={props.ask.onProposal}
                          />
                        </CaseRail>
                      ) : null}
                    </>
                  ),
                  explore: (
                    <>
                      {!loading ? (
                        <ExploreFurther
                          region={regionLink(params, props.onOpenPage)}
                          overview={overviewLink(params, props.onOpenPage)}
                          world={worldLink(params, props.catalogue, props.onOpenPage)}
                          more={
                            <CrossChecks
                              params={params}
                              variables={props.catalogue}
                              regionTypes={props.regionTypes}
                              onOpenPage={props.onOpenPage}
                            />
                          }
                        />
                      ) : null}
                      <SeasonsPanel params={params} investigation={shown} onOpenPage={props.onOpenPage} />
                      <PeriodExplorer params={params} investigation={shown} onOpenCase={props.onOpenCase} />
                      <GapChart investigation={shown} />
                    </>
                  ),
                  evidence: (
                    <>
                      <EvidencePanel investigation={shown} />
                      <PlaceLegend places={mapPlaces} pickedPoint={props.pickedPoint} folded />
                    </>
                  ),
                  learn: <EvidenceLesson />,
                }}
              />
            </div>
          ) : firstLoad ? (
            <ChartSkeleton />
          ) : null}
          {shown !== null ? (
            <StageNote>
              <StageCaption investigation={shown} cellCount={cellCount} />
            </StageNote>
          ) : null}
          {props.notes}
        </>
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
