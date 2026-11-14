import { describe, expect, test } from "vitest";
import type { ChatEvent, Investigation, TrendMap, VariableSummary } from "./api";
import {
  chatReducer,
  chatResult,
  conversationMessages,
  EMPTY_CHAT,
  endedBeforeCheck,
  isRunning,
} from "./chat";
import type { ChatAction, ChatState } from "./chat";

const AIR_TEMPERATURE: VariableSummary = {
  id: "air_temp",
  name: "Air temperature",
  definition: "Air temperature two metres above the ground.",
  units: "°C",
  rate_units: "°C",
  decimals: 2,
  theme: "temperature",
  record_start: 1981,
  related: [],
  region_types: [],
};

const NAIROBI_CASE: Investigation = {
  id: "abc123",
  variable: AIR_TEMPERATURE,
  requested: { from: 1981, to: 2025, season: "annual" },
  results: [
    {
      place: {
        name: "Nairobi",
        lat: -1.29,
        lon: 36.82,
        cell: { lat: -1.5, lon: 36.875, height: 0.5, width: 0.625 },
      },
      series: [],
      trend: null,
      verdict: {
        kind: "no_data",
        direction: null,
        sentence: "There is no air temperature data for this location.",
        cautions: [],
      },
    },
  ],
  steps: [],
  sources: [],
  app_url:
    "https://trend-detective.example.org/case?v=air_temp&p=-1.29,36.82&label=Nairobi&from=1981&to=2025&s=annual",
};

const FINLAND_MAP: TrendMap = {
  variable: AIR_TEMPERATURE,
  requested: { from: 1981, to: 2025, season: "JJA" },
  box: { south: 55, west: 20, north: 65, east: 30 },
  cells: [],
  area_mean: NAIROBI_CASE.results[0] as Investigation["results"][number],
  steps: [],
  sources: [],
  app_url: "/map?v=air_temp&from=1981&to=2025&s=JJA&box=55,20,65,30",
};

function run(actions: readonly ChatAction[], state: ChatState = EMPTY_CHAT): ChatState {
  return actions.reduce(chatReducer, state);
}

function event(value: ChatEvent): ChatAction {
  return { type: "event", event: value };
}

const ASK_NAIROBI: ChatAction = { type: "asked", question: "Is Nairobi getting warmer?" };

function lastTurn(state: ChatState): ChatState["turns"][number] {
  const turn = state.turns.at(-1);
  if (turn === undefined) throw new Error("The conversation has no turn.");
  return turn;
}

describe("chatReducer", () => {
  test("starts a running turn for a question", () => {
    const state = run([ASK_NAIROBI]);
    expect(lastTurn(state)).toMatchObject({
      question: "Is Nairobi getting warmer?",
      status: "running",
      text: "",
    });
    expect(isRunning(state)).toBe(true);
  });

  test("shows a step when it starts and updates it in place when it finishes", () => {
    const step = { id: "step-1", tool: "find_place", label: "Looked up places matching 'Nairobi'" };
    const state = run([
      ASK_NAIROBI,
      event({ event: "step", data: { ...step, status: "started" } }),
      event({ event: "step", data: { ...step, status: "finished" } }),
    ]);
    expect(lastTurn(state).steps).toEqual([{ ...step, status: "finished" }]);
  });

  test("keeps steps in the order they started", () => {
    const state = run([
      ASK_NAIROBI,
      event({ event: "step", data: { id: "step-1", tool: "find_place", label: "A", status: "started" } }),
      event({ event: "step", data: { id: "step-2", tool: "analyze_trend", label: "B", status: "started" } }),
      event({ event: "step", data: { id: "step-1", tool: "find_place", label: "A", status: "failed" } }),
    ]);
    expect(lastTurn(state).steps.map((step) => [step.id, step.status])).toEqual([
      ["step-1", "failed"],
      ["step-2", "started"],
    ]);
  });

  test("joins the text deltas in order", () => {
    const state = run([
      ASK_NAIROBI,
      event({ event: "text", data: { delta: "Air temperature in Nairobi " } }),
      event({ event: "text", data: { delta: "has risen." } }),
    ]);
    expect(lastTurn(state).text).toBe("Air temperature in Nairobi has risen.");
  });

  test("records the unverified numbers of the check", () => {
    const state = run([ASK_NAIROBI, event({ event: "check", data: { unverified: ["0.9"] } })]);
    expect(lastTurn(state).unverified).toEqual(["0.9"]);
  });

  test("links each case the turn put on screen", () => {
    const state = run([ASK_NAIROBI, event({ event: "case", data: { investigation: NAIROBI_CASE } })]);
    expect(lastTurn(state).results).toEqual([
      {
        kind: "case",
        url: "/case?v=air_temp&p=-1.29,36.82&label=Nairobi&from=1981&to=2025&s=annual",
        title: "Air temperature in Nairobi, 1981 to 2025",
      },
    ]);
  });

  test("answers the turn on done", () => {
    const state = run([ASK_NAIROBI, event({ event: "done", data: {} })]);
    expect(lastTurn(state).status).toBe("answered");
    expect(isRunning(state)).toBe(false);
  });

  test("fails the turn on an error event and keeps it failed after done", () => {
    const state = run([
      ASK_NAIROBI,
      event({
        event: "error",
        data: { code: "ai_unavailable", message: "The AI could not answer just now." },
      }),
      event({ event: "done", data: {} }),
    ]);
    expect(lastTurn(state)).toMatchObject({ status: "failed", failure: "The AI could not answer just now." });
  });

  test("fails the turn when the request is refused", () => {
    const state = run([ASK_NAIROBI, { type: "failed", message: "The AI is turned off." }]);
    expect(lastTurn(state)).toMatchObject({ status: "failed", failure: "The AI is turned off." });
  });

  test("stops a running turn", () => {
    expect(lastTurn(run([ASK_NAIROBI, { type: "stopped" }])).status).toBe("stopped");
  });

  test("ignores events that arrive after the turn ended", () => {
    const stopped = run([ASK_NAIROBI, { type: "stopped" }]);
    expect(run([event({ event: "text", data: { delta: "late" } })], stopped)).toBe(stopped);
  });

  test("ignores events when no turn is running", () => {
    expect(run([event({ event: "text", data: { delta: "stray" } })])).toBe(EMPTY_CHAT);
  });

  test("keeps earlier turns when a follow-up is asked", () => {
    const state = run([
      ASK_NAIROBI,
      event({ event: "done", data: {} }),
      { type: "asked", question: "And in Mumbai?" },
    ]);
    expect(state.turns.map((turn) => [turn.question, turn.status])).toEqual([
      ["Is Nairobi getting warmer?", "answered"],
      ["And in Mumbai?", "running"],
    ]);
  });

  test("forgets the conversation on reset", () => {
    expect(run([ASK_NAIROBI, { type: "reset" }])).toEqual(EMPTY_CHAT);
  });
});

describe("endedBeforeCheck", () => {
  const PARTIAL_TEXT = event({ event: "text", data: { delta: "Air temperature in Nairobi has" } });

  test("is true for a turn that failed after some text and before its check", () => {
    const state = run([ASK_NAIROBI, PARTIAL_TEXT, { type: "failed", message: "The connection was lost." }]);
    expect(endedBeforeCheck(lastTurn(state))).toBe(true);
  });

  test("is true for a turn that was stopped after some text and before its check", () => {
    const state = run([ASK_NAIROBI, PARTIAL_TEXT, { type: "stopped" }]);
    expect(endedBeforeCheck(lastTurn(state))).toBe(true);
  });

  test("is false for a turn whose check arrived before it was stopped", () => {
    const state = run([
      ASK_NAIROBI,
      PARTIAL_TEXT,
      event({ event: "check", data: { unverified: [] } }),
      { type: "stopped" },
    ]);
    expect(endedBeforeCheck(lastTurn(state))).toBe(false);
  });

  test("is false for a turn that is still running", () => {
    expect(endedBeforeCheck(lastTurn(run([ASK_NAIROBI, PARTIAL_TEXT])))).toBe(false);
  });

  test("is false for a turn that failed before writing any text", () => {
    const state = run([ASK_NAIROBI, { type: "failed", message: "The AI is turned off." }]);
    expect(endedBeforeCheck(lastTurn(state))).toBe(false);
  });
});

describe("conversationMessages", () => {
  test("sends a first question alone", () => {
    expect(conversationMessages(EMPTY_CHAT, "Is Nairobi getting warmer?")).toEqual([
      { role: "user", text: "Is Nairobi getting warmer?" },
    ]);
  });

  test("resends answered turns as plain text before the new question", () => {
    const state = run([
      ASK_NAIROBI,
      event({ event: "text", data: { delta: "It has risen." } }),
      event({ event: "done", data: {} }),
    ]);
    expect(conversationMessages(state, "And in Mumbai?")).toEqual([
      { role: "user", text: "Is Nairobi getting warmer?" },
      { role: "assistant", text: "It has risen." },
      { role: "user", text: "And in Mumbai?" },
    ]);
  });

  test("leaves out turns that failed, stopped or wrote nothing", () => {
    const state = run([
      ASK_NAIROBI,
      { type: "failed", message: "Too many questions." },
      { type: "asked", question: "Second?" },
      { type: "stopped" },
      { type: "asked", question: "Third?" },
      event({ event: "text", data: { delta: "  " } }),
      event({ event: "done", data: {} }),
    ]);
    expect(conversationMessages(state, "Fourth?")).toEqual([{ role: "user", text: "Fourth?" }]);
  });
});

describe("chatResult", () => {
  test("opens a case at the parameters of the API's own link", () => {
    const result = chatResult({ investigation: NAIROBI_CASE });
    expect(result).toMatchObject({
      kind: "case",
      params: {
        variable: "air_temp",
        places: [{ lat: -1.29, lon: 36.82, name: "Nairobi" }],
        from: 1981,
        to: 2025,
        season: "annual",
      },
      url: "/case?v=air_temp&p=-1.29,36.82&label=Nairobi&from=1981&to=2025&s=annual",
    });
  });

  test("opens a map at the parameters of the API's own link", () => {
    const result = chatResult({ map: FINLAND_MAP });
    expect(result).toMatchObject({
      kind: "map",
      params: {
        variable: "air_temp",
        from: 1981,
        to: 2025,
        season: "JJA",
        box: { south: 55, west: 20, north: 65, east: 30 },
      },
      url: "/map?v=air_temp&from=1981&to=2025&s=JJA&box=55,20,65,30",
      title: "Map of Air temperature, 1981 to 2025",
    });
  });

  test("opens nothing when the link cannot be read", () => {
    expect(chatResult({ investigation: { ...NAIROBI_CASE, app_url: "/case" } })).toBeNull();
  });
});
