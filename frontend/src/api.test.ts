import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Mock } from "vitest";
import { ApiError, discover, explain, getCase, getVariables, streamChat } from "./api";
import type { ChatEvent, ChatRequest } from "./api";

const REQUEST: ChatRequest = { messages: [{ role: "user", text: "Is Nairobi getting warmer?" }] };

let fetchMock: Mock<typeof fetch>;

beforeEach(() => {
  fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function streamResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function collectChat(chunks: string[]): Promise<ChatEvent[]> {
  fetchMock.mockResolvedValue(streamResponse(chunks));
  const events: ChatEvent[] = [];
  await streamChat(REQUEST, (event) => events.push(event));
  return events;
}

describe("streamChat", () => {
  test("posts the conversation as JSON to /api/chat", async () => {
    await collectChat(["event: done\ndata: {}\n\n"]);
    const [path, init] = fetchMock.mock.calls[0] ?? [];
    expect(path).toBe("/api/chat");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify(REQUEST));
  });

  test("passes each event to the callback in order", async () => {
    const events = await collectChat([
      'event: step\ndata: {"id":"1","tool":"find_place","label":"Found Nairobi","status":"finished"}\n\n',
      'event: text\ndata: {"delta":"Nairobi "}\n\n',
      'event: check\ndata: {"unverified":["3.2"]}\n\n',
      "event: done\ndata: {}\n\n",
    ]);
    expect(events).toEqual([
      {
        event: "step",
        data: { id: "1", tool: "find_place", label: "Found Nairobi", status: "finished" },
      },
      { event: "text", data: { delta: "Nairobi " } },
      { event: "check", data: { unverified: ["3.2"] } },
      { event: "done", data: {} },
    ]);
  });

  test("reads events split across chunks, including a CRLF split between its halves", async () => {
    const events = await collectChat([
      "event: te",
      'xt\r\ndata: {"delta":',
      '"hi"}\r',
      "\n\r\nevent: done\r\ndata: {}\r\n\r\n",
    ]);
    expect(events).toEqual([
      { event: "text", data: { delta: "hi" } },
      { event: "done", data: {} },
    ]);
  });

  test("joins multi-line data with a newline", async () => {
    const events = await collectChat([
      'event: text\ndata: {"delta":\ndata: "hi"}\n\n',
      "event: done\ndata: {}\n\n",
    ]);
    expect(events[0]).toEqual({ event: "text", data: { delta: "hi" } });
  });

  test("skips comments and events it does not know", async () => {
    const events = await collectChat([
      ": keep-alive\n\n",
      'event: future\ndata: {"x":1}\n\n',
      "event: done\ndata: {}\n\n",
    ]);
    expect(events).toEqual([{ event: "done", data: {} }]);
  });

  test("passes an error event to the callback", async () => {
    const events = await collectChat([
      'event: error\ndata: {"code":"ai_unavailable","message":"The AI is off."}\n\n',
      "event: done\ndata: {}\n\n",
    ]);
    expect(events[0]).toEqual({
      event: "error",
      data: { code: "ai_unavailable", message: "The AI is off." },
    });
  });

  test("rejects when the stream ends before the done event", async () => {
    fetchMock.mockResolvedValue(streamResponse(['event: text\ndata: {"delta":"hi"}\n\n']));
    await expect(streamChat(REQUEST, () => undefined)).rejects.toMatchObject({
      code: "bad_response",
    });
  });

  test("rejects with the server's error when the turn is refused", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "rate_limited", message: "Too many requests." } }, 429),
    );
    await expect(streamChat(REQUEST, () => undefined)).rejects.toEqual(
      new ApiError("rate_limited", "Too many requests.", 429),
    );
  });
});

describe("JSON endpoints", () => {
  test("getCase calls /api/case with the case's parameter string", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: "abc" }));
    await getCase({ variable: "air_temp", places: [{ lat: 60.17, lon: 24.94 }], season: "annual" });
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/case?v=air_temp&p=60.17,24.94&s=annual");
  });

  test("getVariables leaves out an empty query", async () => {
    fetchMock.mockResolvedValue(jsonResponse([]));
    await getVariables("", "temperature");
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/variables?theme=temperature");
  });

  test("an error in the spec 10 shape becomes an ApiError with its code and message", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "unknown_variable", message: "No such variable." } }, 400),
    );
    const error: unknown = await getVariables("rain").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "unknown_variable", message: "No such variable.", status: 400 });
  });

  test("reads an unsupported request, such as a world mean of snow, with its message", async () => {
    const message = "The whole-world mean covers no snow depth.";
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "unsupported_request", message } }, 422));
    const error: unknown = await getVariables("snow").catch((caught: unknown) => caught);
    expect(error).toMatchObject({ code: "unsupported_request", message, status: 422 });
  });

  test("reads the not_found and internal_error codes the service adds to spec 10", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "internal_error", message: "Something went wrong." } }, 500),
    );
    await expect(getVariables()).rejects.toMatchObject({ code: "internal_error", status: 500 });
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "not_found", message: "No such page." } }, 404),
    );
    await expect(getVariables()).rejects.toMatchObject({ code: "not_found", status: 404 });
  });

  test("an error response that is not JSON becomes a bad_response error with its status", async () => {
    fetchMock.mockResolvedValue(new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(getVariables()).rejects.toMatchObject({ code: "bad_response", status: 502 });
  });

  test("an unreachable server becomes a network_error", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(getVariables()).rejects.toMatchObject({ code: "network_error", status: null });
  });
});

describe("discovery and explanations", () => {
  const ID = "a".repeat(64);

  test("discover posts the question and the unconfirmed draft to /api/discover", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: "clarify" }));
    const draft = { variable: null, places: [], from: null, to: null, season: "annual" as const };
    await discover("What should I study in Singapore?", draft);
    const [path, init] = fetchMock.mock.calls[0] ?? [];
    expect(path).toBe("/api/discover");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ question: "What should I study in Singapore?", draft }));
  });

  test("explain posts the question and the investigation's ID to /api/explain", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: "answered", investigation_id: ID }));
    const answer = await explain("Explain this simply", ID);
    const [path, init] = fetchMock.mock.calls[0] ?? [];
    expect(path).toBe("/api/explain");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ question: "Explain this simply", investigation_id: ID }));
    expect(answer).toMatchObject({ investigation_id: ID });
  });

  test("passes the caller's signal, so a question can be cancelled", async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    const controller = new AbortController();
    await explain("Why?", ID, controller.signal);
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(controller.signal);
  });

  test("reads investigation_unavailable, the error of an investigation no longer on record", async () => {
    const message = "This investigation is not on record. Open the case again.";
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "investigation_unavailable", message } }, 409));
    await expect(explain("Why?", ID)).rejects.toMatchObject({
      code: "investigation_unavailable",
      message,
      status: 409,
    });
  });

  test("an answer that is not JSON becomes a bad_response error", async () => {
    fetchMock.mockResolvedValue(new Response("not json", { status: 200 }));
    await expect(discover("Why?", null)).rejects.toMatchObject({ code: "bad_response", status: 200 });
  });
});
