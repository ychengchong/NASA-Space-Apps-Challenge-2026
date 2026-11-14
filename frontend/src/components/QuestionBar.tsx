import { useEffect, useRef, useState } from "react";
import type { FormEvent, JSX } from "react";
import { getPlaces, getVariables } from "../api";
import type { ClarificationChoice, DiscoveryResponse, VariableSummary } from "../api";
import { joinWords } from "../cautions";
import { discoveryStatusText } from "../discovery";
import { matchQuestion } from "../keywordMatch";
import type { KeywordLookups, KeywordProposal } from "../keywordMatch";
import { afterScreenChange } from "../questionBarState";
import type { QuestionStatus } from "../questionBarState";
import { toApiError } from "../useRequest";
import { DiscoveryResult } from "./DiscoveryResult";

// Spec 3, "What each part of the screen is for": the question bar offers example prompts.
const EXAMPLE_PROMPTS: readonly string[] = [
  "Is Nairobi getting warmer?",
  "Is it getting wetter in Mumbai?",
  "Is the Sahara getting hotter?",
];

const KEYWORD_LOOKUPS: KeywordLookups = {
  findPlaces: (query, signal) => getPlaces(query, signal),
  searchVariables: (query, signal) => getVariables(query, undefined, signal),
};

/**
 * How an AI turn ended: "answered", "ended" without an answer (stopped, or failed after it had
 * already put a result on screen), or "fall_back" when the AI could not take the question and
 * the bar should match keywords instead.
 */
export type AiAnswer = "answered" | "ended" | "fall_back";

/** The built-in AI as the question bar uses it (spec 8). */
export interface AiHelper {
  ask: (question: string) => Promise<AiAnswer>;
  /** True while a turn runs; the bar then takes no new question. */
  working: boolean;
  onStop: () => void;
  /** True once the conversation has a question, so the next one reads as a follow-up. */
  followUp: boolean;
}

/** Guided discovery as the question bar uses it (spec 8, "Guided discovery"). */
export interface DiscoveryHelper {
  /**
   * Sends the question with the settings as they stand, after `choice`'s patch when one was
   * chosen. A "ready" answer's proposal fills the settings before this resolves.
   */
  discover: (
    question: string,
    choice: ClarificationChoice | null,
    signal: AbortSignal,
  ) => Promise<DiscoveryResponse>;
  /** "Use this variable" on a suggestion of `response`. */
  onUseVariable: (variable: VariableSummary, response: DiscoveryResponse) => void;
  /** Opens the case settings to set up the case by hand. */
  onManual: () => void;
  /** The request failed; the bar then matches keywords and shows `message` with a way back. */
  onFailure: (message: string) => void;
}

/** Why the bar fell back to keywords, in the server's words, and a way back to the AI. */
export interface AiNotice {
  message: string;
  onRetry: () => void;
}

/** A complete case the question set up, waiting for the user to run it (spec 3, "Ask"). */
export interface ReadyCase {
  /** The case in words, such as "Air temperature · Helsinki · the full record, all months". */
  summary: string;
  onRun: () => void;
  onEdit: () => void;
}

interface QuestionBarProps {
  /** Called with what keyword mode found, for the user to confirm in the case settings. */
  onProposal: (proposal: KeywordProposal) => void;
  /**
   * Stage 4 (spec 8): when given, a question goes to the AI instead of the keyword matcher.
   * Without it the bar matches keywords and says so (spec 8, "When the AI is off").
   */
  ai?: AiHelper;
  /**
   * Draft 5 (spec 8): when given, a question goes to guided discovery instead of the planner or
   * the keyword matcher.
   */
  discovery?: DiscoveryHelper;
  /** Shown in keyword mode after the AI failed. */
  aiNotice?: AiNotice | null;
  /**
   * True on the first screen, where the bar leads the page: it offers example prompts and wears
   * its accent. On a case or a map it steps back, so the verdict leads.
   */
  firstScreen: boolean;
  /**
   * Rises each time the screen moves on from the last question: a page opens, the browser goes
   * back or forward, or the settings a keyword match filled in are cancelled.
   */
  screenChanges: number;
  /** The case a keyword match set up, when it is complete; shown under the question to run. */
  ready?: ReadyCase | null;
}

/** The entry point: a question in plain words becomes a case, through the AI or keywords. */
export function QuestionBar({
  onProposal,
  ai,
  discovery,
  aiNotice,
  firstScreen,
  screenChanges,
  ready,
}: QuestionBarProps): JSX.Element {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<QuestionStatus>({ kind: "idle" });
  const [seenScreenChanges, setSeenScreenChanges] = useState(screenChanges);
  const controllerRef = useRef<AbortController | null>(null);
  // The discovery request on its way, which a screen change cancels (afterScreenChange).
  const discoveryRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    discoveryRef.current?.abort();
    discoveryRef.current = null;
  }, [screenChanges]);

  // Spec 3: a keyword match is dropped once it no longer describes what is on screen.
  if (screenChanges !== seenScreenChanges) {
    setSeenScreenChanges(screenChanges);
    const bar = afterScreenChange({ question, status });
    setQuestion(bar.question);
    setStatus(bar.status);
  }

  const matchKeywords = (text: string): void => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus({ kind: "working" });
    matchQuestion(text, KEYWORD_LOOKUPS, controller.signal).then(
      (proposal) => {
        if (controller.signal.aborted) return;
        setStatus({ kind: "found", proposal });
        onProposal(proposal);
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setStatus({ kind: "failed", message: toApiError(error).message });
      },
    );
  };

  const askAi = (helper: AiHelper, text: string): void => {
    controllerRef.current?.abort();
    setStatus({ kind: "idle" });
    setQuestion("");
    void helper.ask(text).then((answer) => {
      if (answer === "answered") setStatus({ kind: "ai_answered" });
      if (answer !== "fall_back") return;
      // The question goes back in the box, unless the user has started typing another.
      setQuestion((current) => (current === "" ? text : current));
      matchKeywords(text);
    });
  };

  const askDiscovery = (helper: DiscoveryHelper, text: string, choice: ClarificationChoice | null): void => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    discoveryRef.current = controller;
    setStatus({ kind: "discovering", question: text });
    helper.discover(text, choice, controller.signal).then(
      (response) => {
        if (controller.signal.aborted) return;
        setStatus({ kind: "discovered", question: text, response });
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        // Spec 8, "When the AI is off": the question is matched by keywords instead.
        helper.onFailure(toApiError(error).message);
        setQuestion((current) => (current === "" ? text : current));
        matchKeywords(text);
      },
    );
  };

  const stopDiscovery = (): void => {
    controllerRef.current?.abort();
    setStatus({ kind: "idle" });
  };

  const ask = (text: string): void => {
    const trimmed = text.trim();
    if (trimmed === "") return;
    if (discovery !== undefined) askDiscovery(discovery, trimmed, null);
    else if (ai === undefined) matchKeywords(trimmed);
    else if (!ai.working) askAi(ai, trimmed);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    ask(question);
  };

  const discovering = status.kind === "discovering";
  const working = ai?.working === true || discovering;
  return (
    <section
      className={firstScreen ? "question-bar" : "question-bar is-quiet"}
      aria-labelledby="question-label"
    >
      <form className="question-form" onSubmit={handleSubmit}>
        <label id="question-label" htmlFor="question" className="question-label">
          Ask a question about the Earth
        </label>
        <div className="question-row">
          <input
            id="question"
            ref={inputRef}
            type="text"
            className="question-input"
            value={question}
            placeholder={ai?.followUp === true ? "Ask a follow-up question" : "Is Nairobi getting warmer?"}
            autoComplete="off"
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button type="submit" className="button button-primary" disabled={working}>
            Ask
          </button>
          {working ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={discovering ? stopDiscovery : ai?.onStop}
            >
              Stop
            </button>
          ) : null}
        </div>
      </form>
      {firstScreen ? (
        <div className="prompt-row">
          <span className="prompt-label">Try:</span>
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="prompt-chip"
              disabled={working}
              onClick={() => {
                setQuestion(prompt);
                ask(prompt);
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      ) : null}
      {aiNotice ? (
        <div className="notice notice-warning notice-compact" role="alert">
          <p>{aiNotice.message}</p>
          <button type="button" className="button button-small" onClick={aiNotice.onRetry}>
            Try the AI again
          </button>
        </div>
      ) : null}
      <p className="mode-note">{modeNote(ai, discovery)}</p>
      <p className="status-text" role="status">
        {ai?.working === true
          ? "The AI is proposing settings. It will not run an analysis until you confirm."
          : statusText(status)}
      </p>
      {discovery !== undefined && status.kind === "discovered" ? (
        <DiscoveryResult
          response={status.response}
          disabled={working}
          onChoose={(choice) => {
            // The answer and the pressed button leave the page, so focus waits in the question box.
            inputRef.current?.focus();
            askDiscovery(discovery, status.question, choice);
          }}
          onUseVariable={(variable) => discovery.onUseVariable(variable, status.response)}
          onManual={discovery.onManual}
          onKeywords={() => {
            inputRef.current?.focus();
            matchKeywords(status.question);
          }}
        />
      ) : null}
      {ready ? (
        <div className="notice notice-compact ready-card" role="group" aria-labelledby="ready-label">
          <p>
            <strong id="ready-label">Ready to test:</strong> {ready.summary}
          </p>
          <span className="ready-card-actions">
            <button type="button" className="button button-primary" onClick={ready.onRun}>
              Run this case
            </button>
            <button type="button" className="button button-secondary" onClick={ready.onEdit}>
              Change the settings
            </button>
          </span>
        </div>
      ) : null}
    </section>
  );
}

function modeNote(ai: AiHelper | undefined, discovery: DiscoveryHelper | undefined): string {
  if (discovery !== undefined) {
    return "An AI suggests variables from reviewed documentation, with its sources, and proposes settings. Nothing runs until you confirm.";
  }
  if (ai !== undefined) {
    return "An AI reads your question, runs the tests and writes notes. You can change everything it sets up.";
  }
  return "The AI helper is off. The app looks for a variable, a place and any years among your words, and you check what it found before the case runs.";
}

function statusText(status: QuestionStatus): string {
  switch (status.kind) {
    case "idle":
      return "";
    case "working":
      return "Looking for a variable and a place in your question…";
    case "failed":
      return `The question could not be matched. ${status.message}`;
    case "found":
      return foundText(status.proposal);
    case "ai_answered":
      return "Review the proposed settings and dates, then select Run this case to confirm.";
    case "discovering":
      return "The AI is reading reviewed documentation for your question. Nothing runs until you confirm.";
    case "discovered":
      return discoveryStatusText(status.response);
  }
}

function foundText({ variables, places }: KeywordProposal): string {
  const variable = variables[0]?.name;
  const placeNames = joinWords(places.map((place) => place.name));
  if (variable !== undefined && places.length > 0) {
    return `Found ${variable} and ${placeNames}. Check the case below, then run it.`;
  }
  if (variable !== undefined) {
    return `Found ${variable}, but no place. Search for a place in the case settings.`;
  }
  if (places.length > 0) {
    return `Found ${placeNames}, but no variable. Pick a variable in the case settings.`;
  }
  return "No variable or place matched your words. Pick them in the case settings, or try other words.";
}
