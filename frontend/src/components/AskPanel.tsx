import { useEffect, useReducer, useRef, useState } from "react";
import type { FormEvent, JSX } from "react";
import { aiFeatureStates, setupGapText } from "../aiSetup";
import type { Capabilities, ExplanationBlock, ExplanationResponse, Investigation, Proposal } from "../api";
import { proposalSummary } from "../discovery";
import {
  ASK_IDLE,
  askReducer,
  askStatusText,
  EXPLANATION_PROMPTS,
  EXPLANATION_QUESTION_MAX_LENGTH,
  referenceLabel,
  resolveReference,
  unansweredText,
} from "../explanation";
import type { AskState } from "../explanation";
import { toApiError } from "../useRequest";
import { CitationList } from "./CitationList";

/** Sends one question about an investigation to the server, which loads it by its ID. */
export type Explain = (
  question: string,
  investigationId: string,
  signal: AbortSignal,
) => Promise<ExplanationResponse>;

interface AskPanelProps {
  /** The investigation on screen, whose numbers the answer's references are read from. */
  investigation: Investigation;
  explain: Explain;
  /** New settings an answer proposes: they go into the case settings for the user to confirm. */
  onProposal: (proposal: Proposal) => void;
}

/**
 * "Ask about this investigation" (spec 3 and 8), in the "Answer" tab after the record years.
 * Give it the investigation's ID as its key: a new investigation starts an empty panel, and the
 * question on its way for the old one is cancelled, as it is when the panel leaves the page. The
 * result above never waits for it.
 */
export function AskPanel({ investigation, explain, onProposal }: AskPanelProps): JSX.Element {
  const [question, setQuestion] = useState("");
  const [state, dispatch] = useReducer(askReducer, ASK_IDLE);
  // The questions on their way; a stable set, so the cleanup below sees the ones still open.
  const pendingRef = useRef(new Set<AbortController>());

  useEffect(() => {
    const pending = pendingRef.current;
    return () => {
      for (const controller of pending) controller.abort();
      pending.clear();
    };
  }, []);

  const stopAll = (): void => {
    for (const controller of pendingRef.current) controller.abort();
    pendingRef.current.clear();
  };

  const ask = (text: string): void => {
    const trimmed = text.trim();
    if (trimmed === "") return;
    stopAll();
    const controller = new AbortController();
    pendingRef.current.add(controller);
    dispatch({ type: "ask", question: trimmed });
    explain(trimmed, investigation.id, controller.signal)
      .then(
        (response) => {
          if (controller.signal.aborted) return;
          dispatch({ type: "answer", response, investigationId: investigation.id });
        },
        (error: unknown) => {
          if (controller.signal.aborted) return;
          dispatch({ type: "fail", message: toApiError(error).message });
        },
      )
      .finally(() => pendingRef.current.delete(controller));
  };

  return (
    <AskPanelView
      investigation={investigation}
      question={question}
      state={state}
      onQuestionChange={setQuestion}
      onAsk={(text) => {
        setQuestion(text);
        ask(text);
      }}
      onStop={() => {
        stopAll();
        dispatch({ type: "stop" });
      }}
      onProposal={onProposal}
    />
  );
}

interface AskPanelViewProps {
  investigation: Investigation;
  question: string;
  state: AskState;
  onQuestionChange: (question: string) => void;
  onAsk: (question: string) => void;
  onStop: () => void;
  onProposal: (proposal: Proposal) => void;
}

/** The panel as it looks in each state; AskPanel holds the state. */
export function AskPanelView(props: AskPanelViewProps): JSX.Element {
  const { investigation, question, state } = props;
  const asking = state.kind === "asking";
  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    props.onAsk(question);
  };
  return (
    <section className="panel sheet ask-panel" aria-labelledby="ask-heading">
      <h2 id="ask-heading">Ask about this investigation</h2>
      <p className="panel-note">
        Questions are sent to OpenAI. Answers are written by AI and checked against this result.
      </p>
      <form className="ask-form" onSubmit={handleSubmit}>
        <label htmlFor="ask-question" className="field-hint">
          Your question about the dataset, the method or the limits of this result
        </label>
        <div className="question-row">
          <input
            id="ask-question"
            type="text"
            className="question-input"
            value={question}
            maxLength={EXPLANATION_QUESTION_MAX_LENGTH}
            placeholder="What can't we conclude?"
            autoComplete="off"
            onChange={(event) => props.onQuestionChange(event.target.value)}
          />
          <button type="submit" className="button button-primary" disabled={asking}>
            Ask
          </button>
          {asking ? (
            <button type="button" className="button button-secondary" onClick={props.onStop}>
              Stop
            </button>
          ) : null}
        </div>
      </form>
      <div className="prompt-row">
        <span className="prompt-label">Try:</span>
        {EXPLANATION_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="prompt-chip"
            disabled={asking}
            onClick={() => props.onAsk(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
      <p className="status-text" role="status">
        {askStatusText(state)}
      </p>
      {state.kind === "failed" ? (
        <div className="notice notice-warning notice-compact" role="alert">
          <p>{state.message}</p>
        </div>
      ) : null}
      {state.kind === "answered" ? (
        <AskAnswer investigation={investigation} response={state.response} onProposal={props.onProposal} />
      ) : null}
    </section>
  );
}

interface AskPanelOffProps {
  /** What the server reported; null when it could not be asked. */
  capabilities: Capabilities | null;
}

/**
 * The panel while the server offers no explanations (spec 3 and 8). It takes no question, and
 * says which AI features are on and which settings keep this one off.
 */
export function AskPanelOff({ capabilities }: AskPanelOffProps): JSX.Element {
  const gaps = capabilities?.ai_explanation_gaps ?? [];
  return (
    <section className="panel sheet ask-panel" aria-labelledby="ask-heading">
      <h2 id="ask-heading">Ask about this investigation</h2>
      <p className="panel-note">
        {capabilities === null
          ? "The server did not say whether its AI assistant is set up, so this panel cannot take questions."
          : "The AI assistant is not set up on this server, so this panel cannot take questions."}{" "}
        The result and its "Evidence" and "Learn" tabs work without it.
      </p>
      {capabilities !== null ? (
        <div>
          <h3 id="ask-features-heading" className="ask-setup-heading">
            AI features on this server
          </h3>
          <ul className="plain-list ask-setup-list" aria-labelledby="ask-features-heading">
            {aiFeatureStates(capabilities).map((feature) => (
              <li key={feature.label}>
                {feature.label}: <strong>{feature.on ? "on" : "off"}</strong>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {gaps.length > 0 ? (
        <div>
          <h3 id="ask-gaps-heading" className="ask-setup-heading">
            What keeps this panel off
          </h3>
          <ul className="plain-list ask-setup-list" aria-labelledby="ask-gaps-heading">
            {gaps.map((gap) => {
              const text = setupGapText(gap);
              return (
                <li key={gap}>
                  <code>{text.setting}</code> {text.problem}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
      <p className="field-hint">
        Whoever runs the server sets these in its .env file and then restarts it. The README's "Configure the
        AI assistant" section explains each one.
      </p>
    </section>
  );
}

interface AskAnswerProps {
  investigation: Investigation;
  response: ExplanationResponse;
  onProposal: (proposal: Proposal) => void;
}

function AskAnswer({ investigation, response, onProposal }: AskAnswerProps): JSX.Element {
  if (response.status === "insufficient_evidence") {
    return (
      <div className="notice notice-warning ask-unanswered">
        <p>
          <strong>No checked answer.</strong> {unansweredText(response.reason)}
        </p>
        <p>
          Try another question, or read the "Evidence" and "Learn" tabs, which show the method and its limits
          without AI.
        </p>
      </div>
    );
  }
  const { proposal } = response;
  return (
    <div className="ai-text ask-answer">
      <p className="ai-label">Written by AI</p>
      {response.blocks.map((block, index) => (
        <AnswerBlock key={index} id={`ask-block-${index}`} investigation={investigation} block={block} />
      ))}
      {response.status === "new_investigation_required" ? (
        <div className="notice notice-compact ready-card" role="group" aria-labelledby="ask-proposal-label">
          {proposal != null ? (
            <>
              <p>
                <strong id="ask-proposal-label">This needs a new analysis:</strong>{" "}
                {proposalSummary(proposal)}. Nothing runs until you select Run this case.
              </p>
              {proposal.notices.map((notice, index) => (
                <p key={index} className="panel-note">
                  {notice}
                </p>
              ))}
              <span className="ready-card-actions">
                <button type="button" className="button button-primary" onClick={() => onProposal(proposal)}>
                  Put these in the case settings
                </button>
              </span>
            </>
          ) : (
            <p>
              <strong id="ask-proposal-label">This needs a new analysis.</strong> Set it up in "Change this
              case".
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

interface AnswerBlockProps {
  id: string;
  investigation: Investigation;
  block: ExplanationBlock;
}

/** One block of the answer: the AI's text, the result's own values it points at, and its sources. */
function AnswerBlock({ id, investigation, block }: AnswerBlockProps): JSX.Element {
  return (
    <div className="ask-block">
      <p className="ai-body">{block.text}</p>
      {block.references.length > 0 ? (
        <p id={`${id}-references`} className="field-hint">
          From this result, not written by AI:
        </p>
      ) : null}
      {block.references.length > 0 ? (
        <dl className="ask-references" aria-labelledby={`${id}-references`}>
          {block.references.map((reference, index) => (
            <div key={index} className="ask-reference">
              <dt>{referenceLabel(investigation, reference)}</dt>
              <dd>{resolveReference(investigation, reference)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      <CitationList citations={block.citations} />
    </div>
  );
}
