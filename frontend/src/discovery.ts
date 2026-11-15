/**
 * Guided discovery in the question bar (spec 8, "Guided discovery"): what the settings become
 * after the AI's answer, a clarification choice or a suggested variable. Every result waits in
 * the case settings for "Run this case", so nothing runs before the user confirms it.
 */

import type {
  ClarificationChoice,
  DiscoveryDraft,
  DiscoveryResponse,
  Proposal,
  VariableSuggestion,
  VariableSummary,
} from "./api";
import { caseFromDraft, placeFromCandidate } from "./caseDraft";
import type { CaseDraft } from "./caseDraft";
import { cautionText, joinWords } from "./cautions";
import { MAX_PLACES } from "./caseUrl";
import { seasonMonthsText } from "./seasons";

// Spec 8: discovery offers up to three variables.
export const MAX_SUGGESTIONS = 3;

/** The settings as the server reads them: the unconfirmed draft sent with a question. */
export function toDiscoveryDraft(draft: CaseDraft): DiscoveryDraft {
  return {
    variable: draft.variable,
    places: draft.places.map((place) => ({ lat: place.lat, lon: place.lon, name: place.name ?? null })),
    from: draft.from ?? null,
    to: draft.to ?? null,
    season: draft.season,
  };
}

/** The draft after a clarification choice: each part the choice sets replaces the draft's. */
export function applyChoice(draft: CaseDraft, choice: ClarificationChoice): CaseDraft {
  const next: CaseDraft = { ...draft };
  if (choice.variable != null) next.variable = choice.variable;
  if (choice.place != null) next.places = [placeFromCandidate(choice.place)];
  if (choice.from != null) next.from = choice.from;
  if (choice.to != null) next.to = choice.to;
  if (choice.season != null) next.season = choice.season;
  return next;
}

/**
 * The draft after an AI proposal: its first variable, its places and its dates replace those of
 * `base`, and whatever it leaves open stays as it was.
 */
export function draftFromAiProposal(base: CaseDraft, proposal: Proposal): CaseDraft {
  const places =
    proposal.places.length > 0 ? proposal.places.slice(0, MAX_PLACES).map(placeFromCandidate) : base.places;
  const draft: CaseDraft = {
    ...base,
    variable: proposal.variables[0]?.id ?? base.variable,
    places,
    season: proposal.season,
  };
  if (proposal.from !== null) draft.from = proposal.from;
  if (proposal.to !== null) draft.to = proposal.to;
  return draft;
}

/**
 * Whether the question bar offers its "Ready to test" card for `draft`, the settings after
 * `proposal`: only when the proposal itself named a variable and a place, as for a keyword match
 * (caseDraft.questionIsReady), so a place kept from the open case never runs as the asked one.
 */
export function proposalIsReady(proposal: Proposal, draft: CaseDraft): boolean {
  return proposal.variables.length > 0 && proposal.places.length > 0 && caseFromDraft(draft) !== null;
}

/** The settings after "Use this variable", and whether they are a whole case to offer to run. */
export interface SuggestedDraft {
  draft: CaseDraft;
  ready: boolean;
}

/**
 * "Use this variable": the suggested variable with the answer's proposed places and dates when
 * it has them, or with the settings as they stand.
 */
export function draftWithSuggestion(
  base: CaseDraft,
  response: DiscoveryResponse,
  variableId: string,
): SuggestedDraft {
  const proposal = response.proposal;
  if (proposal == null) return { draft: { ...base, variable: variableId }, ready: false };
  const draft = { ...draftFromAiProposal(base, proposal), variable: variableId };
  return { draft, ready: proposal.places.length > 0 && caseFromDraft(draft) !== null };
}

/** The suggestions the bar shows: never more than three. */
export function shownSuggestions(response: DiscoveryResponse): VariableSuggestion[] {
  return response.suggestions.slice(0, MAX_SUGGESTIONS);
}

/**
 * What the catalogue says about a suggested variable (spec 8: definitions, data availability and
 * limits), in the words the case settings use: its definition, when its record starts, its note
 * and the years its data source changes. None of it is written by AI.
 */
export function catalogueFacts(variable: VariableSummary): string[] {
  const facts = [variable.definition, `The record starts in ${variable.record_start}.`];
  if (variable.trend_note) facts.push(`Note: ${variable.trend_note}`);
  const sourceChange = cautionText("source_change", variable, null);
  if (sourceChange !== null) facts.push(sourceChange);
  return facts;
}

/**
 * The question bar's status line once discovery has answered, so a screen reader hears that the
 * answer is on screen: the proposal is in the settings, a clarification waits, suggestions wait,
 * or there is no suggestion.
 */
export function discoveryStatusText(response: DiscoveryResponse): string {
  if (response.status === "unsupported") return "No suggestion; you can set up the case by hand.";
  if (response.status === "clarify") {
    return "The AI needs one more detail. Pick an answer below, or set up the case by hand.";
  }
  if (response.proposal != null) {
    return "The AI's proposal is in the case settings. Check it, then select Run this case to confirm.";
  }
  return "The AI's suggestions are below. Use one to put it in the case settings.";
}

const MISSING_WORDS: Readonly<Record<DiscoveryResponse["missing"][number], string>> = {
  variable: "the variable",
  place: "the place",
  from: "the first year",
  to: "the last year",
  season: "the months",
};

/**
 * What the question left open. A part the proposal fills, such as dates it proposes, is in the
 * settings already, so the line says to check it: "Your question left open the first year, so
 * the settings hold the proposed defaults. Check them before you run the case." A part it does
 * not fill, or every part without a proposal, is still to choose: "Still to choose in the case
 * settings: the place." Null when nothing is missing.
 */
export function missingText(missing: DiscoveryResponse["missing"], proposal: Proposal | null): string | null {
  if (missing.length === 0) return null;
  const filled = proposal === null ? [] : missing.filter((field) => proposalFills(proposal, field));
  const open = missing.filter((field) => !filled.includes(field));
  const lines: string[] = [];
  if (filled.length > 0) {
    const parts = joinWords(filled.map((field) => MISSING_WORDS[field]));
    lines.push(
      `Your question left open ${parts}, so the settings hold the proposed defaults. Check them before you run the case.`,
    );
  }
  if (open.length > 0) {
    lines.push(
      `Still to choose in the case settings: ${joinWords(open.map((field) => MISSING_WORDS[field]))}.`,
    );
  }
  return lines.join(" ");
}

/**
 * Every note on a discovery answer as one paragraph, so the suggestions are not buried under
 * separate notes: what is still open, then the proposal's notices, then the answer's own, each in
 * the server's words and once only. Null when there is no note.
 */
export function discoveryNotes(response: DiscoveryResponse): string | null {
  const missing = missingText(response.missing, response.proposal ?? null);
  const notes = [
    ...(missing === null ? [] : [missing]),
    ...(response.proposal?.notices ?? []),
    ...response.notices,
  ];
  const unique = [...new Set(notes.map((note) => note.trim()).filter((note) => note !== ""))];
  return unique.length > 0 ? unique.join(" ") : null;
}

function proposalFills(proposal: Proposal, field: DiscoveryResponse["missing"][number]): boolean {
  switch (field) {
    case "variable":
      return proposal.variables.length > 0;
    case "place":
      return proposal.places.length > 0;
    case "from":
      return proposal.from !== null;
    case "to":
      return proposal.to !== null;
    case "season":
      return true;
  }
}

/**
 * A proposal in words, as the "Ready to test" card writes a case: "Air temperature · Helsinki ·
 * 1981 to 2025, all months". A part it leaves open keeps the settings' own, and says so.
 */
export function proposalSummary(proposal: Proposal): string {
  const variable = proposal.variables[0]?.name ?? "the same variable";
  const places =
    proposal.places.length > 0
      ? joinWords(proposal.places.slice(0, MAX_PLACES).map((place) => place.name))
      : "the same places";
  return `${variable} · ${places} · ${proposalPeriodText(proposal)}, ${seasonMonthsText(proposal.season)}`;
}

function proposalPeriodText({ from, to }: Proposal): string {
  if (from !== null && to !== null) return `${from} to ${to}`;
  if (from !== null) return `from ${from}`;
  if (to !== null) return `to ${to}`;
  return "the same period";
}
