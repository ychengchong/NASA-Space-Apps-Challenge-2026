import type { KeywordProposal } from "./keywordMatch";

/** What became of the last question asked in the question bar. */
export type QuestionStatus =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "found"; proposal: KeywordProposal }
  | { kind: "failed"; message: string }
  | { kind: "ai_answered" };

/** What the question bar holds: the text in its box, and what became of the last question. */
export interface QuestionBarState {
  question: string;
  status: QuestionStatus;
}

/**
 * The bar once the screen has moved on from the last question: another page opened, or the
 * settings a keyword match filled in were dropped. A keyword result, found or failed, then
 * describes settings that no longer wait on screen, so it goes together with its question. A
 * question still being typed or matched stays, and so does the AI's answer, whose notes stay on
 * screen from page to page.
 */
export function afterScreenChange(bar: QuestionBarState): QuestionBarState {
  if (bar.status.kind !== "found" && bar.status.kind !== "failed") return bar;
  return { question: "", status: { kind: "idle" } };
}
