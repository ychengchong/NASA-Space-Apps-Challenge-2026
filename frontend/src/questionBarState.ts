import type { DiscoveryResponse } from "./api";
import type { KeywordProposal } from "./keywordMatch";

/** What became of the last question asked in the question bar. */
export type QuestionStatus =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "found"; proposal: KeywordProposal }
  | { kind: "failed"; message: string }
  | { kind: "ai_answered" }
  | { kind: "discovering"; question: string }
  | { kind: "discovered"; question: string; response: DiscoveryResponse };

/** What the question bar holds: the text in its box, and what became of the last question. */
export interface QuestionBarState {
  question: string;
  status: QuestionStatus;
}

/**
 * The bar once the screen has moved on from the last question: another page opened, or the
 * settings a keyword match filled in were dropped. A keyword result, found or failed, and guided
 * discovery's suggestions then describe settings that no longer wait on screen, so they go
 * together with their question. A question on its way to discovery is cancelled (the bar aborts
 * its request), since its answer would fill settings on a page the user has left; its text stays
 * in the box to send again. A question still being typed or matched stays, and so does the AI
 * planner's answer, whose notes stay on screen from page to page.
 */
export function afterScreenChange(bar: QuestionBarState): QuestionBarState {
  const { kind } = bar.status;
  if (kind === "discovering") return { question: bar.question, status: { kind: "idle" } };
  if (kind !== "found" && kind !== "failed" && kind !== "discovered") return bar;
  return { question: "", status: { kind: "idle" } };
}
