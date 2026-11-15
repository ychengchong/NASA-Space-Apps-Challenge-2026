import { describe, expect, test } from "vitest";
import { aiFeatureStates, setupGapText } from "./aiSetup";

describe("setupGapText", () => {
  test("names the setting to change and what is wrong with it", () => {
    expect(setupGapText("no_openai_api_key")).toEqual({ setting: "OPENAI_API_KEY", problem: "is empty." });
  });

  test("tells a corpus version cut short apart from an empty one", () => {
    expect(setupGapText("corpus_version_mismatch").problem).toContain("Copy the whole 64-character version");
    expect(setupGapText("no_corpus_version").problem).toContain("is empty");
  });
});

describe("aiFeatureStates", () => {
  test("lists this panel's feature first, then discovery, then the planner", () => {
    expect(
      aiFeatureStates({
        ai_planner_available: true,
        ai_discovery_available: true,
        ai_explanation_available: false,
      }),
    ).toEqual([
      { label: "Answers in this panel", on: false },
      { label: "Suggested variables in the question bar", on: true },
      { label: "Case settings proposed from a question", on: true },
    ]);
  });

  test("counts a feature an older server does not report as off", () => {
    expect(aiFeatureStates({ ai_planner_available: false }).map((feature) => feature.on)).toEqual([
      false,
      false,
      false,
    ]);
  });
});
