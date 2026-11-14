/**
 * "Ask about this investigation" (spec 8, "Explanations and result protection"): the panel's
 * states, and the result references an answer points at. The AI never writes a number: a
 * reference names an allowlisted field, and its value is read here from the trusted
 * Investigation and written with format.ts, as the evidence panel writes it.
 */

import type {
  ExplanationResponse,
  Investigation,
  PlaceResult,
  ResultReference,
  Trend,
  UnansweredReason,
} from "./api";
import { formatPValue, formatRatePerDecade, formatSignedRate, withUnits } from "./format";
import { seasonLabel } from "./seasons";
import { KIND_LABELS } from "./verdictStamp";

// Spec 3: the explanation prompts the panel offers.
export const EXPLANATION_PROMPTS: readonly string[] = [
  "Explain this simply",
  "What does this dataset actually measure?",
  "What are the limitations here?",
  "What can't we conclude?",
  "What could I investigate next?",
];

// Spec 8: one question of at most 2,000 characters.
export const EXPLANATION_QUESTION_MAX_LENGTH = 2000;

type ResultField = ResultReference["field"];

const FIELD_LABELS: Readonly<Record<ResultField, string>> = {
  sen_slope: "Rate of change (Sen's slope)",
  sen_ci95: "95% confidence interval of the rate",
  mk_p: "Mann-Kendall p-value",
  total_change: "Total change over the years used",
  n: "Number of years used",
  first_year: "First year used",
  last_year: "Last year used",
  "verdict.kind": "Verdict",
  "verdict.sentence": "Verdict sentence",
  "place.name": "Place",
  "variable.name": "Variable",
  "variable.units": "Units",
  "variable.rate_units": "Units of the rate",
  "requested.from": "First year asked for",
  "requested.to": "Last year asked for",
  "requested.season": "Months",
};

const PLACE_FIELDS: ReadonlySet<ResultField> = new Set<ResultField>([
  "sen_slope",
  "sen_ci95",
  "mk_p",
  "total_change",
  "n",
  "first_year",
  "last_year",
  "verdict.kind",
  "verdict.sentence",
  "place.name",
]);

const NOT_AVAILABLE = "Not available";

/** What a reference names, with its place's name in a comparison: "Rate of change (Sen's slope) · Oslo". */
export function referenceLabel(investigation: Investigation, reference: ResultReference): string {
  const label = FIELD_LABELS[reference.field];
  if (!PLACE_FIELDS.has(reference.field) || investigation.results.length < 2) return label;
  const result = investigation.results[reference.place ?? 0];
  return result === undefined ? label : `${label} · ${result.place.name}`;
}

/**
 * The value a reference names, read from the investigation and written as the evidence panel
 * writes it, such as "+0.50 °C per decade". A place the investigation does not hold reads
 * "Not available"; a trend that was not tested reads as the evidence panel says it.
 */
export function resolveReference(investigation: Investigation, reference: ResultReference): string {
  const { variable, requested } = investigation;
  switch (reference.field) {
    case "variable.name":
      return variable.name;
    case "variable.units":
      return variable.units === "" ? "None" : variable.units;
    case "variable.rate_units":
      return variable.rate_units === "" ? "None" : variable.rate_units;
    case "requested.from":
      return String(requested.from);
    case "requested.to":
      return String(requested.to);
    case "requested.season":
      return seasonLabel(requested.season);
  }
  const result = investigation.results[reference.place ?? 0];
  if (result === undefined) return NOT_AVAILABLE;
  return placeValue(investigation, result, reference.field);
}

function placeValue(investigation: Investigation, result: PlaceResult, field: ResultField): string {
  switch (field) {
    case "place.name":
      return result.place.name;
    case "verdict.kind":
      return KIND_LABELS[result.verdict.kind];
    case "verdict.sentence":
      return result.verdict.sentence;
  }
  const { trend } = result;
  if (trend === null) return result.verdict.kind === "no_data" ? "No data" : "Not tested: too few years";
  return trendValue(investigation, trend, field);
}

function trendValue(investigation: Investigation, trend: Trend, field: ResultField): string {
  const { variable } = investigation;
  switch (field) {
    case "sen_slope":
      return formatRatePerDecade(trend.sen_slope, variable);
    case "sen_ci95":
      return trend.sen_ci95 === null
        ? "Unavailable: serial-dependence coverage has not been validated"
        : `${formatSignedRate(trend.sen_ci95[0], variable.decimals)} to ` +
            formatRatePerDecade(trend.sen_ci95[1], variable);
    case "mk_p":
      return trend.mk_p === null ? "Not assessed" : formatPValue(trend.mk_p);
    case "total_change":
      return (
        `${withUnits(formatSignedRate(trend.total_change, variable.decimals), variable.rate_units)} ` +
        `from ${trend.first_year} to ${trend.last_year}`
      );
    case "n":
      return String(trend.n);
    case "first_year":
      return String(trend.first_year);
    case "last_year":
      return String(trend.last_year);
    default:
      return NOT_AVAILABLE;
  }
}

const REASON_TEXT: Readonly<Record<UnansweredReason, string>> = {
  no_evidence: "The reviewed documentation has nothing that answers this question, so the AI gave no answer.",
  provider_refused: "The AI declined to answer this question.",
  provider_incomplete: "The AI did not finish an answer.",
  validation_failed:
    "The AI wrote an answer, but it did not pass the app's checks against this result, so it is not shown.",
  unsupported_question: "This question is outside what the app can explain about this result.",
};

/** Why there is no answer, in plain words. */
export function unansweredText(reason: UnansweredReason | null | undefined): string {
  return reason == null ? "There is no checked answer to this question." : REASON_TEXT[reason];
}

const FINISHED_TEXT: Readonly<Record<ExplanationResponse["status"], string>> = {
  answered: "The answer is below.",
  insufficient_evidence: "There is no checked answer; the reason is below.",
  new_investigation_required: "This needs a new analysis; see below.",
};

/**
 * The panel's status line, which a screen reader announces: that the AI is writing, then what
 * came of it. A failure is announced by its own alert, so the line is then empty.
 */
export function askStatusText(state: AskState): string {
  switch (state.kind) {
    case "asking":
      return "The AI is writing an answer. The result above does not wait for it.";
    case "answered":
      return FINISHED_TEXT[state.response.status];
    case "idle":
    case "failed":
      return "";
  }
}

/** What the panel holds: nothing yet, a question on its way, its answer, or why it failed. */
export type AskState =
  | { kind: "idle" }
  | { kind: "asking"; question: string }
  | { kind: "answered"; question: string; response: ExplanationResponse }
  | { kind: "failed"; question: string; message: string };

export type AskAction =
  | { type: "ask"; question: string }
  | { type: "answer"; response: ExplanationResponse; investigationId: string }
  | { type: "fail"; message: string }
  | { type: "stop" };

export const ASK_IDLE: AskState = { kind: "idle" };

const OTHER_INVESTIGATION =
  "The answer was about another investigation, so it is not shown. Ask the question again.";

/**
 * The panel after `action`. An answer or a failure counts only for the question on its way; an
 * answer bound to another investigation than the one on screen is never shown (spec 8).
 */
export function askReducer(state: AskState, action: AskAction): AskState {
  switch (action.type) {
    case "ask":
      return { kind: "asking", question: action.question };
    case "stop":
      return ASK_IDLE;
    case "answer":
      if (state.kind !== "asking") return state;
      if (action.response.investigation_id !== action.investigationId) {
        return { kind: "failed", question: state.question, message: OTHER_INVESTIGATION };
      }
      return { kind: "answered", question: state.question, response: action.response };
    case "fail":
      if (state.kind !== "asking") return state;
      return { kind: "failed", question: state.question, message: action.message };
  }
}
