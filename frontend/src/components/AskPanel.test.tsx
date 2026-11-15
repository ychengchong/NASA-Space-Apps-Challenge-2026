import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { Capabilities, ExplanationResponse, Proposal } from "../api";
import type { AskState } from "../explanation";
import { AskPanel, AskPanelOff, AskPanelView } from "./AskPanel";
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

describe("AskPanelOff", () => {
  const PLANNER_ONLY: Capabilities = {
    ai_planner_available: true,
    ai_discovery_available: false,
    ai_explanation_available: false,
    ai_explanation_gaps: ["no_vector_store", "corpus_version_mismatch"],
  };

  test("keeps the heading but takes no question", () => {
    const html = renderToStaticMarkup(<AskPanelOff capabilities={PLANNER_ONLY} />);
    expect(html).toContain('<h2 id="ask-heading">Ask about this investigation</h2>');
    expect(html).toContain("The AI assistant is not set up on this server");
    expect(html).not.toContain("<input");
    expect(html).not.toContain("<button");
  });

  test("says which AI features are on", () => {
    const html = renderToStaticMarkup(<AskPanelOff capabilities={PLANNER_ONLY} />);
    expect(html).toContain("Answers in this panel: <strong>off</strong>");
    expect(html).toContain("Suggested variables in the question bar: <strong>off</strong>");
    expect(html).toContain("Case settings proposed from a question: <strong>on</strong>");
  });

  test("names each setting that keeps it off, in the server's order", () => {
    const html = renderToStaticMarkup(<AskPanelOff capabilities={PLANNER_ONLY} />);
    const store = html.indexOf("<code>RAG_VECTOR_STORE_ID</code> is empty.");
    const version = html.indexOf("<code>RAG_CORPUS_VERSION</code> does not match the corpus");
    expect(store).toBeGreaterThan(-1);
    expect(version).toBeGreaterThan(store);
  });

  test("lists no settings when the server names none", () => {
    const html = renderToStaticMarkup(
      <AskPanelOff capabilities={{ ai_planner_available: false, ai_explanation_available: false }} />,
    );
    expect(html).toContain("AI features on this server");
    expect(html).not.toContain("What keeps this panel off");
  });

  test("says it cannot tell when the server could not be asked", () => {
    const html = renderToStaticMarkup(<AskPanelOff capabilities={null} />);
    expect(html).toContain("The server did not say whether its AI assistant is set up");
    expect(html).not.toContain("AI features on this server");
  });
});
