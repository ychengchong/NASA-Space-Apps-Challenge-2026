import type { JSX } from "react";
import type { ChatStep } from "../api";
import { endedBeforeCheck } from "../chat";
import type { ChatTurn } from "../chat";
import { followInApp } from "../links";
import { splitUnverified } from "../numberCheck";

interface DetectiveNotesProps {
  turns: readonly ChatTurn[];
  onNewConversation: () => void;
  /** Opens a case or map the AI ran, inside the app. */
  onOpenPage: (url: string) => void;
}

/**
 * The AI's reading of the case (spec 3 and spec 8, "What appears on screen"): each step as it
 * runs, then the AI's text, labelled as written by AI. Its words are shown exactly as written,
 * hypotheses included, with each number the number check could not match marked "unverified".
 */
export function DetectiveNotes({
  turns,
  onNewConversation,
  onOpenPage,
}: DetectiveNotesProps): JSX.Element | null {
  const shown = turns.filter(hasNotes);
  const latest = shown.at(-1);
  if (latest === undefined) return null;
  const earlier = shown.slice(0, -1);
  return (
    <section className="panel notes" aria-labelledby="notes-heading">
      <div className="panel-heading-row">
        <h2 id="notes-heading">Detective notes</h2>
        <button type="button" className="button button-small" onClick={onNewConversation}>
          New conversation
        </button>
      </div>
      {earlier.length > 0 ? (
        <details className="disclosure notes-earlier">
          <summary>Earlier in this conversation</summary>
          {earlier.map((turn, index) => (
            <NotesTurn key={index} turn={turn} onOpenPage={onOpenPage} />
          ))}
        </details>
      ) : null}
      <NotesTurn turn={latest} onOpenPage={onOpenPage} />
    </section>
  );
}

/** A turn that failed before anything happened is left to the question bar's notice. */
function hasNotes(turn: ChatTurn): boolean {
  return turn.status === "running" || turn.steps.length > 0 || turn.text !== "";
}

function NotesTurn({ turn, onOpenPage }: { turn: ChatTurn; onOpenPage: (url: string) => void }): JSX.Element {
  const running = turn.status === "running";
  return (
    <article className="notes-turn" aria-busy={running}>
      <p className="notes-question">
        <span className="notes-who">You asked:</span> {turn.question}
      </p>
      {turn.steps.length > 0 ? (
        <ol className="ai-steps" aria-label="Steps the AI took">
          {turn.steps.map((step) => (
            <StepItem key={step.id} step={step} turnRunning={running} />
          ))}
        </ol>
      ) : null}
      {running && turn.text === "" ? <p className="status-text">The AI is working on it…</p> : null}
      {turn.text !== "" ? (
        <AiText text={turn.text} unverified={turn.unverified ?? []} unchecked={endedBeforeCheck(turn)} />
      ) : null}
      {turn.results.length > 0 ? (
        <div className="notes-results">
          <p className="notes-who">Opened for this answer:</p>
          <ul className="plain-list">
            {turn.results.map((result, index) => (
              <li key={index}>
                <a href={result.url} onClick={(event) => followInApp(event, result.url, onOpenPage)}>
                  {result.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {turn.status === "failed" && turn.failure !== null ? <p className="caution">{turn.failure}</p> : null}
      {turn.status === "stopped" ? <p className="status-text">You stopped this answer.</p> : null}
    </article>
  );
}

/** A step that started in a turn that has ended without finishing it is shown as cut off. */
type StepShown = ChatStep["status"] | "cut_off";

const STEP_ICONS: Readonly<Record<StepShown, string>> = {
  started: "…",
  finished: "✓",
  failed: "✕",
  cut_off: "–",
};

const STEP_WORDS: Readonly<Record<StepShown, string>> = {
  started: "running",
  finished: "done",
  failed: "failed",
  cut_off: "not finished",
};

/** A step's status shows as an icon and a word, never by colour alone. */
function StepItem({ step, turnRunning }: { step: ChatStep; turnRunning: boolean }): JSX.Element {
  const shown: StepShown = step.status === "started" && !turnRunning ? "cut_off" : step.status;
  return (
    <li className={`ai-step ai-step-${shown}`}>
      <span className="ai-step-icon" aria-hidden="true">
        {STEP_ICONS[shown]}
      </span>
      <span>
        {step.label}{" "}
        <span className={shown === "finished" ? "visually-hidden" : "ai-step-word"}>
          ({STEP_WORDS[shown]})
        </span>
      </span>
    </li>
  );
}

/**
 * The AI's words as text nodes, never as HTML, with each unverified number marked in place.
 * `unchecked` is true for the text of a turn that ended before the number check ran.
 */
function AiText({
  text,
  unverified,
  unchecked,
}: {
  text: string;
  unverified: readonly string[];
  unchecked: boolean;
}): JSX.Element {
  const spans = splitUnverified(text, unverified);
  return (
    <div className="ai-text">
      <p className="ai-label">Written by AI</p>
      <p className="ai-body">
        {spans.map((span, index) =>
          span.unverified ? (
            <span key={index} className="unverified">
              <span className="unverified-number">{span.text}</span>{" "}
              <span className="unverified-tag">unverified</span>
            </span>
          ) : (
            span.text
          ),
        )}
      </p>
      {unverified.length > 0 ? (
        <p className="field-hint">
          A number marked unverified does not match any number the app worked out for this answer. Check it
          against the verdict and the evidence.
        </p>
      ) : null}
      {unchecked ? <p className="field-hint">This answer ended before its numbers were checked.</p> : null}
    </div>
  );
}
