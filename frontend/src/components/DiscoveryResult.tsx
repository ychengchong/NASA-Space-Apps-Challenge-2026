import type { JSX } from "react";
import type { ClarificationChoice, DiscoveryResponse, VariableSummary } from "../api";
import { catalogueFacts, discoveryNotes, shownSuggestions } from "../discovery";
import { CitationList } from "./CitationList";

interface DiscoveryResultProps {
  response: DiscoveryResponse;
  /** True while another question is on its way, so no choice is sent twice. */
  disabled: boolean;
  /** A clarification choice: its patch goes into the settings and the question is asked again. */
  onChoose: (choice: ClarificationChoice) => void;
  /** "Use this variable": fills the settings for the user to confirm. */
  onUseVariable: (variable: VariableSummary) => void;
  /** Opens the case settings to set up the case by hand. */
  onManual: () => void;
  /** Looks for a variable and a place among the question's words instead. */
  onKeywords: () => void;
}

/**
 * Guided discovery's answer under the question (spec 8): a short clarification question with its
 * choices, up to three variables with the AI's reason and the cited sources (the catalogue's facts
 * folded under each), then every note in one paragraph, or why there is no suggestion with a way
 * on. The AI's words are plain text under an AI label. Nothing runs from
 * here: every button fills the settings, which wait for "Run this case".
 */
export function DiscoveryResult(props: DiscoveryResultProps): JSX.Element {
  const { response, disabled } = props;
  if (response.status === "unsupported") {
    return (
      <div className="notice notice-warning notice-compact discovery" role="group" aria-label="No suggestion">
        {response.notices.map((notice, index) => (
          <p key={index}>{notice}</p>
        ))}
        <span className="ready-card-actions">
          <button type="button" className="button button-secondary" onClick={props.onManual}>
            Set up the case by hand
          </button>
          <button
            type="button"
            className="button button-secondary"
            disabled={disabled}
            onClick={props.onKeywords}
          >
            Match the words instead
          </button>
        </span>
      </div>
    );
  }
  const suggestions = shownSuggestions(response);
  const notes = discoveryNotes(response);
  const { clarification } = response;
  return (
    <section className="discovery" aria-labelledby="discovery-heading">
      <h2 id="discovery-heading" className="visually-hidden">
        What the AI suggests
      </h2>
      <p className="ai-label">Written by AI</p>
      {clarification != null ? (
        <div className="discovery-clarify" role="group" aria-labelledby="clarify-question">
          <p id="clarify-question" className="ai-body">
            {clarification.question}
          </p>
          {clarification.choices.length > 0 ? (
            <div className="choice-row">
              {clarification.choices.map((choice, index) => (
                <button
                  key={index}
                  type="button"
                  className="button button-secondary"
                  disabled={disabled}
                  onClick={() => props.onChoose(choice)}
                >
                  {choice.label}
                </button>
              ))}
            </div>
          ) : (
            <p className="field-hint">Answer it in a new question, or choose the settings by hand.</p>
          )}
        </div>
      ) : null}
      {suggestions.length > 0 ? (
        <ul className="suggestion-list">
          {suggestions.map((suggestion) => (
            <li key={suggestion.variable.id} className="suggestion-card">
              <h3 id={`suggestion-${suggestion.variable.id}`} className="suggestion-name">
                {suggestion.variable.name}
              </h3>
              <p className="ai-body">{suggestion.reason}</p>
              <CitationList citations={suggestion.citations} />
              <button
                type="button"
                className="button button-secondary"
                aria-describedby={`suggestion-${suggestion.variable.id}`}
                onClick={() => props.onUseVariable(suggestion.variable)}
              >
                Use this variable
              </button>
              {/* The catalogue's own facts stay one tap away, so the AI's reason and its source
                  are read first. */}
              <details className="disclosure suggestion-catalogue">
                <summary>About this variable (from the catalogue, not written by AI)</summary>
                {catalogueFacts(suggestion.variable).map((fact, index) => (
                  <p key={index}>{fact}</p>
                ))}
              </details>
            </li>
          ))}
        </ul>
      ) : null}
      {notes !== null ? <p className="panel-note discovery-notes">{notes}</p> : null}
    </section>
  );
}
