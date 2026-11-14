/**
 * Types and a typed client for the backend's REST and chat endpoints (spec sections 5 and 10).
 *
 * The types mirror backend/app/models.py field for field. A Python field with a default of None
 * is `field?: T | null`; a required field that may be missing data is `T | null`.
 */

import {
  buildCaseQuery,
  buildMapQuery,
  buildOverviewQuery,
  buildSeriesQuery,
  buildWorldQuery,
} from "./caseUrl";
import type { CaseParams, MapParams, OverviewParams, SeriesParams, WorldParams } from "./caseUrl";

import type * as Models from "./generatedModels";

export type Proposal = Models.Proposal;
export type Capabilities = Models.Capabilities;
export type Season = Models.Season;
export type Resolution = Models.Resolution;
export type VerdictKind = Models.VerdictKind;
export type Direction = Models.Direction;
export type Contrast = Models.Contrast;
export type Caution = Models.Caution;
export type PlaceKind = Models.PlaceKind;
export type Box = Models.Box;
export type VariableSummary = Models.VariableSummary;
export type PlaceCandidate = Models.PlaceCandidate;
export type Cell = Models.Cell;
export type Place = Models.Place;
export type SeriesValue = Models.SeriesValue;
export type Series = Models.Series;
export type Requested = Models.Requested;
export type YearValue = Models.YearValue;
export type ScanPoint = Models.ScanPoint;
export type Trend = Models.Trend;
export type Verdict = Models.Verdict;
export type PlaceResult = Models.PlaceResult;
export type Records = Models.Records;
export type SeasonRates = Models.SeasonRates;
export type PlaceOverview = Models.PlaceOverview;
export type Gap = Models.Gap;
export type WorldTrend = Models.WorldTrend;
export type OverviewRow = Models.OverviewRow;
export type SeasonRate = Models.SeasonRate;
export type PlaceSeasons = Models.PlaceSeasons;
export type RecordYear = Models.RecordYear;
export type SourceRef = Models.SourceRef;
export type Investigation = Models.Investigation;
export type MapCell = Models.MapCell;
export type TrendMap = Models.TrendMap;

// Other endpoint shapes (spec 10)

/** One entry of `GET /api/examples`; `query` is a case's parameter string. */
export interface ExampleCase {
  title: string;
  teaser: string;
  query: string;
}

export type SeriesFormat = "json" | "csv";

// Errors (spec 10, "Errors")

const ERROR_CODES = [
  "unknown_variable",
  "bad_place",
  "bad_period",
  "bad_request",
  "unsupported_request",
  "rate_limited",
  "source_unavailable",
  "ai_unavailable",
  "not_found",
  "internal_error",
] as const;

export type ErrorCode = (typeof ERROR_CODES)[number];

export interface ErrorDetail {
  code: ErrorCode;
  message: string;
}

export interface ErrorBody {
  error: ErrorDetail;
}

/**
 * Codes the client adds for failures that never reached the spec 10 error shape:
 * the server could not be reached, or it answered with something this client cannot read.
 */
export type ClientErrorCode = "network_error" | "bad_response";

export class ApiError extends Error {
  readonly code: ErrorCode | ClientErrorCode;
  /** The HTTP status, or null when no response arrived. */
  readonly status: number | null;

  constructor(code: ErrorCode | ClientErrorCode, message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

// Chat (spec 10, "Chat request and stream")

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  /** The parameter string of the case on screen, as written by buildCaseQuery. */
  case?: string;
}

export interface ChatStep {
  id: string;
  tool: string;
  label: string;
  status: "started" | "finished" | "failed";
}

export type ChatCase = { investigation: Investigation } | { map: TrendMap };

export type ChatEvent =
  | { event: "step"; data: ChatStep }
  | { event: "case"; data: ChatCase }
  | { event: "text"; data: { delta: string } }
  | { event: "check"; data: { unverified: string[] } }
  | { event: "error"; data: ErrorDetail }
  | { event: "done"; data: Record<string, never> };

type ChatEventName = ChatEvent["event"];

const CHAT_EVENT_NAMES: readonly ChatEventName[] = ["step", "case", "text", "check", "error", "done"];

// Client

/** Lists catalogue variables matching the words in `query` and the optional `theme`. */
export function getVariables(
  query?: string,
  theme?: string,
  signal?: AbortSignal,
): Promise<VariableSummary[]> {
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (theme) params.set("theme", theme);
  return getJson<VariableSummary[]>(withQuery("/api/variables", params.toString()), signal);
}

/** Finds up to five places whose names match `query`. */
export function getPlaces(query: string, signal?: AbortSignal): Promise<PlaceCandidate[]> {
  const params = new URLSearchParams({ query });
  return getJson<PlaceCandidate[]>(`/api/places?${params.toString()}`, signal);
}

/** Runs a case for one to four places. */
export function getCase(params: CaseParams, signal?: AbortSignal): Promise<Investigation> {
  return getJson<Investigation>(`/api/case?${buildCaseQuery(params)}`, signal);
}

/** Every variable's descriptive rate at one place (spec 7, "What is changing here?"). */
export function getOverview(params: OverviewParams, signal?: AbortSignal): Promise<PlaceOverview> {
  return getJson<PlaceOverview>(`/api/overview?${buildOverviewQuery(params)}`, signal);
}

/** A variable's trend in the frozen whole-world sample (spec 7, "The whole world"). */
export function getWorld(params: WorldParams, signal?: AbortSignal): Promise<WorldTrend> {
  return getJson<WorldTrend>(`/api/world?${buildWorldQuery(params)}`, signal);
}

/** Every season's descriptive rate for a case (spec 7, "All seasons at once"). */
export function getSeasons(params: CaseParams, signal?: AbortSignal): Promise<SeasonRates> {
  return getJson<SeasonRates>(`/api/seasons?${buildCaseQuery(params)}`, signal);
}

/** The address of a place's raw values, for a download link. */
export function seriesUrl(params: SeriesParams): string {
  return `/api/series?${buildSeriesQuery(params)}`;
}

/** The values of one place at one resolution, as JSON (`GET /api/series`). */
export function getSeries(params: Omit<SeriesParams, "format">, signal?: AbortSignal): Promise<Series> {
  return getJson<Series>(seriesUrl({ ...params, format: "json" }), signal);
}

/** Runs the per-cell trends for a box. */
export function getMap(params: MapParams, signal?: AbortSignal): Promise<TrendMap> {
  return getJson<TrendMap>(`/api/map?${buildMapQuery(params)}`, signal);
}

export function getExamples(signal?: AbortSignal): Promise<ExampleCase[]> {
  return getJson<ExampleCase[]>("/api/examples", signal);
}

/**
 * Sends one AI turn and calls `onEvent` for each server-sent event, in order.
 *
 * Resolves after the `done` event. An `error` event is passed to `onEvent` like any other.
 * Rejects with an ApiError when the request is refused, as with `ai_unavailable`, or when the
 * stream ends before `done`. Aborting `signal` rejects with the browser's AbortError.
 */
export async function streamChat(
  request: ChatRequest,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await send("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(request),
    signal,
  });
  if (response.body === null) {
    throw new ApiError("bad_response", "The chat answer was empty.", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = new ServerSentEventParser();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const message of parser.push(decoder.decode(value, { stream: true }))) {
      const event = toChatEvent(message);
      if (event === null) continue;
      onEvent(event);
      if (event.event === "done") {
        await reader.cancel();
        return;
      }
    }
  }
  throw new ApiError("bad_response", "The chat answer stopped before it was complete.", response.status);
}

function withQuery(path: string, query: string): string {
  return query === "" ? path : `${path}?${query}`;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await send(path, { headers: { Accept: "application/json" }, signal });
  try {
    const body: unknown = await response.json();
    return body as T;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new ApiError("bad_response", "The server's answer could not be read.", response.status);
    }
    throw error;
  }
}

/** Ask only for proposed settings. The caller must wait for user confirmation before getCase. */
export async function proposeCase(question: string, signal?: AbortSignal): Promise<Proposal> {
  const response = await send("/api/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  const body: unknown = await response.json();
  return body as Proposal;
}

export function getCapabilities(signal?: AbortSignal): Promise<Capabilities> {
  return getJson<Capabilities>("/api/capabilities", signal);
}

/** Fetches, turning an unreachable server or an error status into an ApiError. */
async function send(path: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    // fetch() rejects with a TypeError when the network fails; an AbortError passes through.
    if (error instanceof TypeError) {
      throw new ApiError("network_error", "The server could not be reached.");
    }
    throw error;
  }
  if (!response.ok) throw await errorFromResponse(response);
  return response;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch (error) {
    // A body that is not JSON, such as a proxy's HTML page, is reported below by its status.
    if (!(error instanceof SyntaxError)) throw error;
  }
  if (isErrorBody(body)) {
    return new ApiError(body.error.code, body.error.message, response.status);
  }
  return new ApiError(
    "bad_response",
    `The server answered with an unexpected error (HTTP ${response.status}).`,
    response.status,
  );
}

function isErrorBody(value: unknown): value is ErrorBody {
  if (!isRecord(value) || !isRecord(value.error)) return false;
  const { code, message } = value.error;
  return isErrorCode(code) && typeof message === "string";
}

function isErrorCode(value: unknown): value is ErrorCode {
  return ERROR_CODES.some((code) => code === value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toChatEvent(message: ServerSentEvent): ChatEvent | null {
  // Events this client does not know are skipped, so the server can add new ones safely.
  const name = CHAT_EVENT_NAMES.find((known) => known === message.event);
  if (name === undefined) return null;
  let data: unknown;
  try {
    data = JSON.parse(message.data);
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new ApiError("bad_response", `The chat sent an unreadable "${name}" event.`);
    }
    throw error;
  }
  return { event: name, data } as ChatEvent;
}

interface ServerSentEvent {
  event: string;
  data: string;
}

const LINE_BREAK = /\r\n|\r|\n/;

/**
 * Splits a server-sent event stream into events, following the HTML standard's parsing rules.
 * Text may arrive in chunks of any size, split anywhere.
 */
class ServerSentEventParser {
  private buffer = "";
  private eventName = "";
  private dataLines: string[] = [];

  push(text: string): ServerSentEvent[] {
    this.buffer += text;
    // A trailing "\r" may be the first half of "\r\n", so it waits for the next chunk.
    const end = this.buffer.endsWith("\r") ? this.buffer.length - 1 : this.buffer.length;
    const lines = this.buffer.slice(0, end).split(LINE_BREAK);
    this.buffer = (lines.pop() ?? "") + this.buffer.slice(end);

    const events: ServerSentEvent[] = [];
    for (const line of lines) {
      const event = this.readLine(line);
      if (event !== null) events.push(event);
    }
    return events;
  }

  private readLine(line: string): ServerSentEvent | null {
    if (line === "") return this.dispatch();
    // A line starting with a colon is a comment, such as a keep-alive ping.
    if (line.startsWith(":")) return null;

    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") this.eventName = value;
    if (field === "data") this.dataLines.push(value);
    return null;
  }

  private dispatch(): ServerSentEvent | null {
    const event =
      this.dataLines.length === 0
        ? null
        : { event: this.eventName || "message", data: this.dataLines.join("\n") };
    this.eventName = "";
    this.dataLines = [];
    return event;
  }
}
