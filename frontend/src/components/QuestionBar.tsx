import { useRef, useState } from "react";
import type { FormEvent, JSX } from "react";
import { getPlaces, getVariables } from "../api";
import { joinWords } from "../cautions";
import { matchQuestion } from "../keywordMatch";
import type { KeywordLookups, KeywordProposal } from "../keywordMatch";
import { toApiError } from "../useRequest";

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

/** Why the bar fell back to keywords, in the server's words, and a way back to the AI. */
export interface AiNotice {
  message: string;
  onRetry: () => void;
}

type Status =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "found"; proposal: KeywordProposal }
  | { kind: "failed"; message: string }
  | { kind: "ai_answered" };

interface QuestionBarProps {
  /** Called with what keyword mode found, for the user to confirm in the case settings. */
  onProposal: (proposal: KeywordProposal) => void;
  /**
   * Stage 4 (spec 8): when given, a question goes to the AI instead of the keyword matcher.
   * Without it the bar matches keywords and says so (spec 8, "When the AI is off").
   */
  ai?: AiHelper;
  /** Shown in keyword mode after the AI failed. */
  aiNotice?: AiNotice | null;
  /** Shows example prompts; an open case leaves them out to keep its verdict near the top. */
  showPrompts: boolean;
}

/** The entry point: a question in plain words becomes a case, through the AI or keywords. */
export function QuestionBar({ onProposal, ai, aiNotice, showPrompts }: QuestionBarProps): JSX.Element {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const controllerRef = useRef<AbortController | null>(null);

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

  const ask = (text: string): void => {
    const trimmed = text.trim();
    if (trimmed === "") return;
    if (ai === undefined) matchKeywords(trimmed);
    else if (!ai.working) askAi(ai, trimmed);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    ask(question);
  };

  const working = ai?.working === true;
  return (
    <section className="question-bar" aria-labelledby="question-label">
      <form className="question-form" onSubmit={handleSubmit}>
        <label id="question-label" htmlFor="question" className="question-label">
          Ask a question about the Earth
        </label>
        <div className="question-row">
          <input
            id="question"
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
            <button type="button" className="button button-secondary" onClick={ai?.onStop}>
              Stop
            </button>
          ) : null}
        </div>
      </form>
      {showPrompts ? (
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
      <p className="mode-note">
        {ai === undefined
          ? "The AI helper is off. The app looks for a variable and a place among your words, and you check what it found in the case settings."
          : "An AI reads your question, runs the tests and writes notes. You can change everything it sets up."}
      </p>
      <p className="status-text" role="status">
        {working
          ? "The AI is proposing settings. It will not run an analysis until you confirm."
          : statusText(status)}
      </p>
    </section>
  );
}

function statusText(status: Status): string {
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
  }
}

function foundText({ variables, places }: KeywordProposal): string {
  const variable = variables[0]?.name;
  const placeNames = joinWords(places.map((place) => place.name));
  if (variable !== undefined && places.length > 0) {
    return `Found ${variable} and ${placeNames}. Check the case settings, then run the case.`;
  }
  if (variable !== undefined) {
    return `Found ${variable}, but no place. Search for a place in the case settings.`;
  }
  if (places.length > 0) {
    return `Found ${placeNames}, but no variable. Pick a variable in the case settings.`;
  }
  return "No variable or place matched your words. Pick them in the case settings, or try other words.";
}
