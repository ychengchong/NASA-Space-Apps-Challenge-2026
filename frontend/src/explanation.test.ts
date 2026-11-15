import { describe, expect, test } from "vitest";
import type { ExplanationResponse, Investigation, ResultReference, Verdict } from "./api";
import { investigation, placeResult, SIGNIFICANT_RISE } from "./components/testData";
import {
  ASK_IDLE,
  askReducer,
  askStatusText,
  referenceLabel,
  resolveReference,
  unansweredText,
} from "./explanation";
import type { AskState } from "./explanation";

type Field = ResultReference["field"];

const HELSINKI = investigation(SIGNIFICANT_RISE);

// One entry for every allowlisted field: the type checker fails this file when one is added.
const VALUES: Readonly<Record<Field, string>> = {
  sen_slope: "+0.05 °C per decade",
  sen_ci95: "+0.03 to +0.07 °C per decade",
  mk_p: "0.001",
  total_change: "+2.20 °C from 1981 to 2025",
  n: "45",
  first_year: "1981",
  last_year: "2025",
  "verdict.kind": "Significant",
  "verdict.sentence": SIGNIFICANT_RISE.sentence,
  "place.name": "Helsinki",
  "variable.name": "Air temperature",
  "variable.units": "°C",
  "variable.rate_units": "°C",
  "requested.from": "1981",
  "requested.to": "2025",
  "requested.season": "Every month",
};

const LABELS: Readonly<Record<Field, string>> = {
  sen_slope: "Rate of change (Sen's slope)",
  sen_ci95: "95% confidence interval of the rate",
  mk_p: "Mann-Kendall p-value",
  total_change: "Total change over the years used",
  n: "Number of years used",
  first_year: "First year used",
  last_year: "Last year used",
  "verdict.kind": "Verdict",
  "verdict.sentence": "Verdict sentence",
  "place.name": "Place",
  "variable.name": "Variable",
  "variable.units": "Units",
  "variable.rate_units": "Units of the rate",
  "requested.from": "First year asked for",
  "requested.to": "Last year asked for",
  "requested.season": "Months",
};

const FIELDS = Object.keys(VALUES) as Field[];
const TREND_FIELDS: readonly Field[] = [
  "sen_slope",
  "sen_ci95",
  "mk_p",
  "total_change",
  "n",
  "first_year",
  "last_year",
];

function comparison(): Investigation {
  const oslo = placeResult({ ...SIGNIFICANT_RISE, sentence: "Oslo's sentence." });
  const second = {
    ...oslo,
    place: { ...oslo.place, name: "Oslo" },
    trend: oslo.trend === null ? null : { ...oslo.trend, sen_slope: -0.125, n: 30 },
  };
  return { ...HELSINKI, results: [...HELSINKI.results, second] };
}

function withoutTrend(verdict: Verdict): Investigation {
  return { ...HELSINKI, results: [{ ...placeResult(verdict), trend: null }] };
}

describe("resolveReference", () => {
  test.each(FIELDS)("writes %s from the investigation", (field) => {
    expect(resolveReference(HELSINKI, { field })).toBe(VALUES[field]);
  });

  test("reads a per-place field from the place the reference names", () => {
    const pair = comparison();
    expect(resolveReference(pair, { field: "place.name", place: 1 })).toBe("Oslo");
    expect(resolveReference(pair, { field: "sen_slope", place: 1 })).toBe("-0.12 °C per decade");
    expect(resolveReference(pair, { field: "n", place: 1 })).toBe("30");
    expect(resolveReference(pair, { field: "verdict.sentence", place: 1 })).toBe("Oslo's sentence.");
  });

  test("reads the first place when the reference names none", () => {
    expect(resolveReference(comparison(), { field: "place.name" })).toBe("Helsinki");
  });

  test("says a place the investigation does not hold is not available", () => {
    expect(resolveReference(HELSINKI, { field: "sen_slope", place: 2 })).toBe("Not available");
  });

  test.each(TREND_FIELDS)("says %s was not tested when a record was too short", (field) => {
    const short = withoutTrend({
      kind: "too_few_years",
      direction: null,
      sentence: "Too short.",
      cautions: [],
    });
    expect(resolveReference(short, { field })).toBe("Not tested: too few years");
  });

  test("says a place without values has no data", () => {
    const empty = withoutTrend({ kind: "no_data", direction: null, sentence: "No data.", cautions: [] });
    expect(resolveReference(empty, { field: "sen_slope" })).toBe("No data");
    expect(resolveReference(empty, { field: "verdict.kind" })).toBe("No data");
  });

  test("says why the rate's interval is missing", () => {
    const [result] = HELSINKI.results;
    if (result?.trend == null) throw new Error("The test data has a trend.");
    const open = { ...HELSINKI, results: [{ ...result, trend: { ...result.trend, sen_ci95: null } }] };
    expect(resolveReference(open, { field: "sen_ci95" })).toBe(
      "Unavailable: serial-dependence coverage has not been validated",
    );
  });

  test("says a p-value that was not assessed is not assessed", () => {
    const [result] = HELSINKI.results;
    if (result?.trend == null) throw new Error("The test data has a trend.");
    const open = { ...HELSINKI, results: [{ ...result, trend: { ...result.trend, mk_p: null } }] };
    expect(resolveReference(open, { field: "mk_p" })).toBe("Not assessed");
  });

  test("writes a p-value below the floor as the evidence panel does", () => {
    const [result] = HELSINKI.results;
    if (result?.trend == null) throw new Error("The test data has a trend.");
    const tiny = { ...HELSINKI, results: [{ ...result, trend: { ...result.trend, mk_p: 0.00001 } }] };
    expect(resolveReference(tiny, { field: "mk_p" })).toBe("< 0.001");
  });

  test("says a variable without units has none", () => {
    const plain = { ...HELSINKI, variable: { ...HELSINKI.variable, units: "", rate_units: "" } };
    expect(resolveReference(plain, { field: "variable.units" })).toBe("None");
    expect(resolveReference(plain, { field: "variable.rate_units" })).toBe("None");
    expect(resolveReference(plain, { field: "sen_slope" })).toBe("+0.05 per decade");
  });

  test("names the months of a season", () => {
    const summer = { ...HELSINKI, requested: { ...HELSINKI.requested, season: "JJA" as const } };
    expect(resolveReference(summer, { field: "requested.season" })).toBe("June to August");
  });
});

describe("referenceLabel", () => {
  test.each(FIELDS)("names %s", (field) => {
    expect(referenceLabel(HELSINKI, { field })).toBe(LABELS[field]);
  });

  test("names the place of a per-place field in a comparison", () => {
    expect(referenceLabel(comparison(), { field: "sen_slope", place: 1 })).toBe(
      "Rate of change (Sen's slope) · Oslo",
    );
  });

  test("names no place for a field of the whole investigation", () => {
    expect(referenceLabel(comparison(), { field: "variable.name" })).toBe("Variable");
  });
});

describe("unansweredText", () => {
  test.each([
    ["no_evidence", "The reviewed documentation has nothing that answers this question"],
    ["provider_refused", "The AI declined"],
    ["provider_incomplete", "did not finish"],
    ["validation_failed", "did not pass the app's checks"],
    ["unsupported_question", "outside what the app can explain"],
  ] as const)("says in plain words why %s gives no answer", (reason, words) => {
    expect(unansweredText(reason)).toContain(words);
  });

  test("still says something without a reason", () => {
    expect(unansweredText(null)).toBe("There is no checked answer to this question.");
  });
});

function explanation(overrides: Partial<ExplanationResponse> = {}): ExplanationResponse {
  return {
    status: "answered",
    investigation_id: HELSINKI.id,
    corpus_version: "v1",
    blocks: [],
    written_by_ai: true,
    ...overrides,
  };
}

const ASKING: AskState = { kind: "asking", question: "Explain this simply" };

describe("askReducer", () => {
  test("sends a question", () => {
    expect(askReducer(ASK_IDLE, { type: "ask", question: "Why?" })).toEqual({
      kind: "asking",
      question: "Why?",
    });
  });

  test("shows the answer bound to the investigation on screen", () => {
    const response = explanation();
    expect(askReducer(ASKING, { type: "answer", response, investigationId: HELSINKI.id })).toEqual({
      kind: "answered",
      question: "Explain this simply",
      response,
    });
  });

  test("never shows an answer bound to another investigation", () => {
    const response = explanation({ investigation_id: "f".repeat(64) });
    const next = askReducer(ASKING, { type: "answer", response, investigationId: HELSINKI.id });
    expect(next.kind).toBe("failed");
  });

  test("drops an answer that arrives after the question was stopped", () => {
    const response = explanation();
    expect(askReducer(ASK_IDLE, { type: "answer", response, investigationId: HELSINKI.id })).toBe(ASK_IDLE);
  });

  test("shows why a question failed", () => {
    expect(askReducer(ASKING, { type: "fail", message: "Busy." })).toEqual({
      kind: "failed",
      question: "Explain this simply",
      message: "Busy.",
    });
  });

  test("drops a failure that arrives after the question was stopped", () => {
    expect(askReducer(ASK_IDLE, { type: "fail", message: "Busy." })).toBe(ASK_IDLE);
  });

  test("stops a question on its way", () => {
    expect(askReducer(ASKING, { type: "stop" })).toBe(ASK_IDLE);
  });

  test("replaces an answer with the next question", () => {
    const answered = askReducer(ASKING, {
      type: "answer",
      response: explanation(),
      investigationId: HELSINKI.id,
    });
    expect(askReducer(answered, { type: "ask", question: "And?" })).toEqual({
      kind: "asking",
      question: "And?",
    });
  });
});

describe("askStatusText", () => {
  const response = (status: ExplanationResponse["status"]): ExplanationResponse => ({
    status,
    investigation_id: HELSINKI.id,
    corpus_version: "v1",
    blocks: [],
    written_by_ai: true,
  });
  const answered = (status: ExplanationResponse["status"]): AskState => ({
    kind: "answered",
    question: "Why?",
    response: response(status),
  });

  test("says the AI is writing while a question is on its way", () => {
    expect(askStatusText({ kind: "asking", question: "Why?" })).toBe(
      "The AI is writing an answer. The result above does not wait for it.",
    );
  });

  test("says what came of the question once it is answered", () => {
    expect(askStatusText(answered("answered"))).toBe("The answer is below.");
    expect(askStatusText(answered("insufficient_evidence"))).toBe(
      "There is no checked answer; the reason is below.",
    );
    expect(askStatusText(answered("new_investigation_required"))).toBe(
      "This needs a new analysis; see below.",
    );
  });

  test("leaves a failure to its alert", () => {
    expect(askStatusText({ kind: "failed", question: "Why?", message: "Busy." })).toBe("");
    expect(askStatusText(ASK_IDLE)).toBe("");
  });
});
