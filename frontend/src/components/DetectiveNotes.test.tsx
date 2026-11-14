import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { ChatTurn } from "../chat";
import { DetectiveNotes } from "./DetectiveNotes";

const PARTIAL_TEXT = "Air temperature in Nairobi has risen by about";
const UNCHECKED_NOTICE = "This answer ended before its numbers were checked.";

function turn(changes: Partial<ChatTurn>): ChatTurn {
  return {
    question: "Is Nairobi getting warmer?",
    steps: [],
    text: PARTIAL_TEXT,
    unverified: null,
    results: [],
    status: "running",
    failure: null,
    ...changes,
  };
}

function renderNotes(shown: ChatTurn): string {
  return renderToStaticMarkup(
    <DetectiveNotes turns={[shown]} onNewConversation={() => undefined} onOpenPage={() => undefined} />,
  );
}

describe("DetectiveNotes", () => {
  test("keeps the text of a failed turn, with a notice under it that its numbers were not checked", () => {
    const html = renderNotes(turn({ status: "failed", failure: "The AI could not answer just now." }));
    expect(html).toContain(PARTIAL_TEXT);
    expect(html.indexOf(UNCHECKED_NOTICE)).toBeGreaterThan(html.indexOf(PARTIAL_TEXT));
  });

  test("keeps the text of a stopped turn, with a notice under it that its numbers were not checked", () => {
    const html = renderNotes(turn({ status: "stopped" }));
    expect(html).toContain(PARTIAL_TEXT);
    expect(html.indexOf(UNCHECKED_NOTICE)).toBeGreaterThan(html.indexOf(PARTIAL_TEXT));
  });

  test("gives no such notice for a turn whose numbers were checked", () => {
    const html = renderNotes(turn({ status: "answered", unverified: [] }));
    expect(html).not.toContain(UNCHECKED_NOTICE);
  });

  test("gives no such notice while the turn is still running", () => {
    expect(renderNotes(turn({ status: "running" }))).not.toContain(UNCHECKED_NOTICE);
  });
});
