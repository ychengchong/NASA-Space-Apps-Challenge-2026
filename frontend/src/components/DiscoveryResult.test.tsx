import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { DiscoveryResponse } from "../api";
import { DiscoveryResult } from "./DiscoveryResult";
import { AIR_TEMP, CITATION, PROJECT_CITATION } from "./testData";

const NOTICE = "These suggestions are written by AI from the cited passages.";

function response(overrides: Partial<DiscoveryResponse> = {}): DiscoveryResponse {
  return {
    status: "ready",
    suggestions: [{ variable: AIR_TEMP, reason: "Heat matters in a city.", citations: [CITATION] }],
    proposal: null,
    missing: [],
    clarification: null,
    notices: [NOTICE],
    written_by_ai: true,
    corpus_version: "v1",
    ...overrides,
  };
}

function render(answer: DiscoveryResponse): string {
  return renderToStaticMarkup(
    <DiscoveryResult
      response={answer}
      disabled={false}
      onChoose={() => undefined}
      onUseVariable={() => undefined}
      onManual={() => undefined}
      onKeywords={() => undefined}
    />,
  );
}

describe("DiscoveryResult", () => {
  test("labels the AI's words", () => {
    expect(render(response())).toContain("Written by AI");
  });

  test("shows each suggestion's variable, reason, sources and a way to use it", () => {
    const html = render(response());
    expect(html).toContain("Air temperature");
    expect(html).toContain("Heat matters in a city.");
    expect(html).toContain(`href="${CITATION.url}"`);
    expect(html).toContain(
      "NASA Langley Research Center, POWER Project · POWER Meteorological Data Sources · MERRA-2",
    );
    expect(html).toContain("Show the cited passage");
    expect(html).toContain(CITATION.passage);
    expect(html).toContain("Use this variable");
  });

  test("marks the project's own notes apart from NASA's documents", () => {
    const html = render(
      response({ suggestions: [{ variable: AIR_TEMP, reason: "Why.", citations: [PROJECT_CITATION] }] }),
    );
    expect(html).toContain("a note by this project, not by NASA");
  });

  test("shows at most three suggestions", () => {
    const suggestions = ["a", "b", "c", "d"].map((id) => ({
      variable: { ...AIR_TEMP, id, name: `Variable ${id}` },
      reason: "Why.",
      citations: [CITATION],
    }));
    const html = render(response({ suggestions }));
    expect(html.match(/Use this variable/g)).toHaveLength(3);
    expect(html).not.toContain("Variable d");
  });

  test("asks the clarification question with its choices as buttons", () => {
    const html = render(
      response({
        status: "clarify",
        suggestions: [],
        clarification: {
          question: "Which place do you mean?",
          choices: [
            { label: "Paris, France", place: { name: "Paris", lat: 48.85, lon: 2.35, kind: "city" } },
            { label: "Paris, Texas", place: { name: "Paris", lat: 33.66, lon: -95.56, kind: "city" } },
          ],
        },
      }),
    );
    expect(html).toContain("Which place do you mean?");
    expect(html).toMatch(/<button[^>]*>Paris, France<\/button>/);
    expect(html).toMatch(/<button[^>]*>Paris, Texas<\/button>/);
  });

  test("offers a way on when a clarification has no choice left", () => {
    const html = render(
      response({ status: "clarify", suggestions: [], clarification: { question: "Which?", choices: [] } }),
    );
    expect(html).toContain("Answer it in a new question, or choose the settings by hand.");
  });

  test("names what is still to choose", () => {
    expect(render(response({ missing: ["place"] }))).toContain(
      "Still to choose in the case settings: the place.",
    );
  });

  test("says the settings hold the proposal's defaults for what the question left open", () => {
    const proposal = {
      variables: [AIR_TEMP],
      places: [],
      from: 1981,
      to: 2025,
      season: "annual" as const,
      notices: [],
    };
    expect(render(response({ missing: ["from"], proposal }))).toContain(
      "Your question left open the first year, so the settings hold the proposed defaults.",
    );
  });

  test("shows the server's notice", () => {
    expect(render(response())).toContain(NOTICE);
  });

  test("shows the notices of the proposal, such as a place still to choose", () => {
    const proposal = {
      variables: [AIR_TEMP],
      places: [],
      from: 1981,
      to: 2025,
      season: "annual" as const,
      notices: ["Choose the intended location for 'Atlantis' in the place search."],
    };
    expect(render(response({ proposal }))).toContain(
      "Choose the intended location for &#x27;Atlantis&#x27; in the place search.",
    );
  });

  test("gives each suggestion the catalogue's definition, record start and note, apart from the AI's words", () => {
    const variable = { ...AIR_TEMP, trend_note: "Read early years with care." };
    const html = render(response({ suggestions: [{ variable, reason: "Why.", citations: [CITATION] }] }));
    const details = html.slice(html.indexOf('<details class="disclosure suggestion-catalogue">'));
    expect(details).toContain(
      "<summary>About this variable (from the catalogue, not written by AI)</summary>",
    );
    expect(details).toContain(AIR_TEMP.definition);
    expect(details).toContain("The record starts in 1981.");
    expect(details).toContain("Note: Read early years with care.");
    expect(details).not.toContain("Why.");
  });

  test("puts the AI's reason, its sources and the button before the catalogue's facts", () => {
    const html = render(
      response({ suggestions: [{ variable: AIR_TEMP, reason: "Why.", citations: [CITATION] }] }),
    );
    const reason = html.indexOf('<p class="ai-body">Why.</p>');
    const sources = html.indexOf('class="citation-list"');
    const button = html.indexOf(">Use this variable</button>");
    const facts = html.indexOf('<details class="disclosure suggestion-catalogue">');
    expect(reason).toBeGreaterThan(-1);
    expect([reason, sources, button, facts]).toEqual(
      [...[reason, sources, button, facts]].sort((a, b) => a - b),
    );
  });

  test("shows every note in one paragraph after the suggestions", () => {
    const html = render(
      response({
        proposal: {
          variables: [AIR_TEMP],
          places: [],
          from: 1981,
          to: 2025,
          season: "annual",
          notices: ["Dates were unspecified."],
          written_by_ai: true,
        },
        notices: ["These suggestions are written by AI."],
      }),
    );
    expect(html.match(/class="panel-note discovery-notes"/g)).toHaveLength(1);
    expect(html).toContain("Dates were unspecified. These suggestions are written by AI.</p>");
  });

  test("says why there is no suggestion and offers the manual way and keyword matching", () => {
    const html = render(
      response({
        status: "unsupported",
        reason: "no_evidence",
        suggestions: [],
        notices: ["No reviewed documentation matched this question."],
      }),
    );
    expect(html).toContain("No reviewed documentation matched this question.");
    expect(html).toContain("Set up the case by hand");
    expect(html).toContain("Match the words instead");
    expect(html).not.toContain("Written by AI");
  });

  test("writes the AI's text as text, never as HTML", () => {
    const html = render(
      response({
        suggestions: [{ variable: AIR_TEMP, reason: "<img src=x onerror=alert(1)>", citations: [] }],
      }),
    );
    expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;");
    expect(html).not.toContain("<img");
  });
});
