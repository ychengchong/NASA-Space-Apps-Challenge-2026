import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { ExplanationResponse, Proposal } from "../api";
import type { AskState } from "../explanation";
import { AskPanel, AskPanelView } from "./AskPanel";
import { AIR_TEMP, CITATION, investigation, SIGNIFICANT_RISE } from "./testData";

const HELSINKI = investigation(SIGNIFICANT_RISE);
const QUESTION = "What does this dataset actually measure?";

function explanation(overrides: Partial<ExplanationResponse> = {}): ExplanationResponse {
  return {
    status: "answered",
    investigation_id: HELSINKI.id,
    corpus_version: "v1",
    blocks: [
      {
        text: "The values describe the grid cell that contains the place.",
        citations: [CITATION],
        references: [{ field: "sen_slope" }, { field: "requested.from" }],
      },
    ],
    written_by_ai: true,
    ...overrides,
  };
}

function render(state: AskState): string {
  return renderToStaticMarkup(
    <AskPanelView
      investigation={HELSINKI}
      question=""
      state={state}
      onQuestionChange={() => undefined}
      onAsk={() => undefined}
      onStop={() => undefined}
      onProposal={() => undefined}
    />,
  );
}

function answered(response: ExplanationResponse): string {
  return render({ kind: "answered", question: QUESTION, response });
}

describe("AskPanel", () => {
  test("starts with its heading, the OpenAI notice, a question box and the example questions", () => {
    const html = renderToStaticMarkup(
      <AskPanel
        investigation={HELSINKI}
        explain={() => Promise.reject(new Error("not called"))}
        onProposal={() => undefined}
      />,
    );
    expect(html).toContain("Ask about this investigation");
    expect(html).toContain(
      "Questions are sent to OpenAI. Answers are written by AI and checked against this result.",
    );
    expect(html).toContain('<label for="ask-question"');
    expect(html).toContain('id="ask-question"');
    expect(html).toContain('maxLength="2000"');
    expect(html).toMatch(/<button type="submit"[^>]*>Ask<\/button>/);
    expect(html).toContain("What can&#x27;t we conclude?");
    expect(html).not.toContain("Stop");
  });

  test("offers to stop a question on its way, and says the result does not wait", () => {
    const html = render({ kind: "asking", question: QUESTION });
    expect(html).toContain("Stop");
    expect(html).toContain("The result above does not wait for it.");
    expect(html).toMatch(/<button type="submit"[^>]*disabled=""[^>]*>Ask<\/button>/);
  });

  test("shows an answer's blocks under an AI label", () => {
    const html = answered(explanation());
    expect(html).toContain("Written by AI");
    expect(html).toContain("The values describe the grid cell that contains the place.");
  });

  test("writes the values an answer points at from the investigation, apart from the AI's text", () => {
    const html = answered(explanation());
    expect(html).toContain("From this result, not written by AI:");
    expect(html).toContain("<dt>Rate of change (Sen&#x27;s slope)</dt><dd>+0.05 °C per decade</dd>");
    expect(html).toContain("<dt>First year asked for</dt><dd>1981</dd>");
  });

  test("links each source and holds its passage behind a disclosure", () => {
    const html = answered(explanation());
    expect(html).toContain(`href="${CITATION.url}"`);
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("<summary>Show the cited passage</summary>");
    expect(html).toContain(CITATION.passage);
  });

  test("says in plain words why there is no answer, with a way on", () => {
    const html = answered(
      explanation({ status: "insufficient_evidence", reason: "validation_failed", blocks: [] }),
    );
    expect(html).toContain("No checked answer.");
    expect(html).toContain("did not pass the app&#x27;s checks against this result");
    expect(html).toContain("Try another question");
    expect(html).not.toContain("Written by AI");
  });

  test("offers new settings for a question that needs a new analysis, without running them", () => {
    const proposal: Proposal = {
      variables: [AIR_TEMP],
      places: [],
      from: 1990,
      to: 2020,
      season: "JJA",
      notices: [],
      written_by_ai: true,
    };
    const html = answered(explanation({ status: "new_investigation_required", proposal }));
    expect(html).toContain("This needs a new analysis:");
    expect(html).toContain("Air temperature · the same places · 1990 to 2020, June to August");
    expect(html).toContain("Nothing runs until you select Run this case.");
    expect(html).toContain("Put these in the case settings");
  });

  test("shows the server's notices with a proposed new analysis", () => {
    const notice = "Choose the intended location for 'Atlantis' in the place search.";
    const proposal: Proposal = {
      variables: [AIR_TEMP],
      places: [],
      from: 1990,
      to: 2020,
      season: "JJA",
      notices: [notice],
      written_by_ai: true,
    };
    const html = answered(explanation({ status: "new_investigation_required", proposal }));
    expect(html).toContain("Choose the intended location for &#x27;Atlantis&#x27; in the place search.");
  });

  test("announces that the answer has arrived", () => {
    expect(answered(explanation())).toMatch(/role="status">The answer is below.</);
  });

  test("points to the settings when a new analysis comes without a proposal", () => {
    const html = answered(explanation({ status: "new_investigation_required", blocks: [], proposal: null }));
    expect(html).toContain("This needs a new analysis.");
    expect(html).not.toContain("Put these in the case settings");
  });

  test("says why a question failed", () => {
    const html = render({ kind: "failed", question: QUESTION, message: "The AI is busy. Try again soon." });
    expect(html).toContain('role="alert"');
    expect(html).toContain("The AI is busy. Try again soon.");
  });

  test("writes the AI's text as text, never as HTML", () => {
    const html = answered(
      explanation({
        blocks: [{ text: '<a href="https://evil.example">click</a>', citations: [CITATION], references: [] }],
      }),
    );
    expect(html).toContain("&lt;a href=&quot;https://evil.example&quot;&gt;click&lt;/a&gt;");
    expect(html).not.toContain('href="https://evil.example"');
  });
});
