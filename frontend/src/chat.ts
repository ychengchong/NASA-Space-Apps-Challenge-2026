/**
 * The conversation with the built-in AI as the screen holds it (spec 8, "One turn"). It lives in
 * memory only: a reload, or "New conversation", forgets it. Only plain text turns are resent.
 */

import type { ChatCase, ChatEvent, ChatMessage, ChatStep, Investigation, TrendMap } from "./api";
import { parseCaseQuery, parseMapQuery } from "./caseUrl";
import type { CaseParams, MapParams } from "./caseUrl";
import { joinWords } from "./cautions";
import { appUrlQuery, casePageUrl, mapPageUrl } from "./route";

/**
 * A turn runs until the stream's `done`. It is then answered, or failed when the server sent an
 * `error` event or the request did not go through; stopped when the user stopped it.
 */
export type TurnStatus = "running" | "answered" | "failed" | "stopped";

/** A case or a map the AI put on screen, as a link that opens it again. */
export interface ChatResultLink {
  kind: "case" | "map";
  url: string;
  title: string;
}

export interface ChatTurn {
  question: string;
  /** Each tool call, in the order it started, with its latest status. */
  steps: ChatStep[];
  /** The AI's text so far. */
  text: string;
  /** Numbers in `text` the number check could not match; null until the check arrives. */
  unverified: string[] | null;
  results: ChatResultLink[];
  status: TurnStatus;
  /** Why the turn failed, in the server's words; null unless it failed. */
  failure: string | null;
}

export interface ChatState {
  turns: ChatTurn[];
}

export type ChatAction =
  | { type: "asked"; question: string }
  | { type: "event"; event: ChatEvent }
  /** The request failed before or during the stream, such as a 503 or a lost connection. */
  | { type: "failed"; message: string }
  | { type: "stopped" }
  | { type: "reset" };

export const EMPTY_CHAT: ChatState = { turns: [] };

/** What a `case` event opens: the case or map, its page parameters, its address and a title. */
export type ChatResult =
  | { kind: "case"; params: CaseParams; url: string; title: string; investigation: Investigation }
  | { kind: "map"; params: MapParams; url: string; title: string; map: TrendMap };

/** The state after `action`. Events and failures change only a turn that is still running. */
export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "asked":
      return { turns: [...state.turns, newTurn(action.question)] };
    case "reset":
      return EMPTY_CHAT;
    case "event":
      return updateRunningTurn(state, (turn) => applyEvent(turn, action.event));
    case "failed":
      return updateRunningTurn(state, (turn) => ({ ...turn, status: "failed", failure: action.message }));
    case "stopped":
      return updateRunningTurn(state, (turn) => ({ ...turn, status: "stopped" }));
  }
}

/** True while the last turn waits for the end of its stream. */
export function isRunning(state: ChatState): boolean {
  return state.turns.at(-1)?.status === "running";
}

/**
 * True when a turn failed or was stopped after writing some text but before its `check` event
 * arrived. Its text stays on screen, but no number in it was checked.
 */
export function endedBeforeCheck(turn: ChatTurn): boolean {
  const ended = turn.status === "failed" || turn.status === "stopped";
  return ended && turn.text !== "" && turn.unverified === null;
}

/**
 * The request's messages for a new question: every answered turn as a user and an assistant
 * message, then the question. A turn without an answer is left out, so the conversation the
 * server reads always alternates and never holds an empty message.
 */
export function conversationMessages(state: ChatState, question: string): ChatMessage[] {
  const messages: ChatMessage[] = [];
  for (const turn of state.turns) {
    if (turn.status !== "answered" || turn.text.trim() === "") continue;
    messages.push({ role: "user", text: turn.question }, { role: "assistant", text: turn.text });
  }
  messages.push({ role: "user", text: question });
  return messages;
}

/**
 * The page a `case` event opens. Its parameters come from the result's `app_url`, the API's own
 * link to it, so the page asks for exactly the case the AI ran. Null when that link cannot be read.
 */
export function chatResult(data: ChatCase): ChatResult | null {
  if ("investigation" in data) {
    const investigation = data.investigation;
    const parsed = parseCaseQuery(appUrlQuery(investigation.app_url));
    if (!parsed.ok) return null;
    return {
      kind: "case",
      params: parsed.value,
      url: casePageUrl(parsed.value),
      title: caseTitle(investigation),
      investigation,
    };
  }
  const map = data.map;
  const parsed = parseMapQuery(appUrlQuery(map.app_url));
  if (!parsed.ok) return null;
  return { kind: "map", params: parsed.value, url: mapPageUrl(parsed.value), title: mapTitle(map), map };
}

function caseTitle({ variable, results, requested }: Investigation): string {
  const places = joinWords(results.map((result) => result.place.name));
  return `${variable.name} in ${places}, ${requested.from} to ${requested.to}`;
}

function mapTitle({ variable, requested }: TrendMap): string {
  return `Map of ${variable.name}, ${requested.from} to ${requested.to}`;
}

function newTurn(question: string): ChatTurn {
  return { question, steps: [], text: "", unverified: null, results: [], status: "running", failure: null };
}

function updateRunningTurn(state: ChatState, update: (turn: ChatTurn) => ChatTurn): ChatState {
  const last = state.turns.at(-1);
  if (last?.status !== "running") return state;
  return { turns: [...state.turns.slice(0, -1), update(last)] };
}

function applyEvent(turn: ChatTurn, event: ChatEvent): ChatTurn {
  switch (event.event) {
    case "step":
      return { ...turn, steps: withStep(turn.steps, event.data) };
    case "case": {
      const result = chatResult(event.data);
      if (result === null) return turn;
      return {
        ...turn,
        results: [...turn.results, { kind: result.kind, url: result.url, title: result.title }],
      };
    }
    case "text":
      return { ...turn, text: turn.text + event.data.delta };
    case "check":
      return { ...turn, unverified: event.data.unverified };
    case "error":
      return { ...turn, status: "failed", failure: event.data.message };
    case "done":
      return { ...turn, status: "answered" };
  }
}

/** The steps with `step` updated in place when its id is known, or added at the end. */
function withStep(steps: readonly ChatStep[], step: ChatStep): ChatStep[] {
  const known = steps.some((existing) => existing.id === step.id);
  return known ? steps.map((existing) => (existing.id === step.id ? step : existing)) : [...steps, step];
}
