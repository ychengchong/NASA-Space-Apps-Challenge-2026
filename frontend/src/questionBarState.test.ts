import { describe, expect, test } from "vitest";
import { afterScreenChange } from "./questionBarState";
import type { QuestionBarState } from "./questionBarState";

const QUESTION = "Is Nairobi getting warmer?";

describe("afterScreenChange", () => {
  test("drops a keyword match and its question", () => {
    const bar: QuestionBarState = {
      question: QUESTION,
      status: { kind: "found", proposal: { variables: [], places: [] } },
    };
    expect(afterScreenChange(bar)).toEqual({ question: "", status: { kind: "idle" } });
  });

  test("drops a keyword match that failed and its question", () => {
    const bar: QuestionBarState = {
      question: QUESTION,
      status: { kind: "failed", message: "No connection." },
    };
    expect(afterScreenChange(bar)).toEqual({ question: "", status: { kind: "idle" } });
  });

  test("keeps a question that is still being typed", () => {
    const bar: QuestionBarState = { question: "Is Nai", status: { kind: "idle" } };
    expect(afterScreenChange(bar)).toBe(bar);
  });

  test("keeps a question that is still being matched", () => {
    const bar: QuestionBarState = { question: QUESTION, status: { kind: "working" } };
    expect(afterScreenChange(bar)).toBe(bar);
  });

  test("keeps the AI's answer and a follow-up typed after it", () => {
    const bar: QuestionBarState = { question: "And in July?", status: { kind: "ai_answered" } };
    expect(afterScreenChange(bar)).toBe(bar);
  });
});
