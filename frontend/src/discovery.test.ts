import { describe, expect, test } from "vitest";
import type { DiscoveryResponse, PlaceCandidate, Proposal, VariableSuggestion } from "./api";
import { EMPTY_DRAFT } from "./caseDraft";
import type { CaseDraft } from "./caseDraft";
import { AIR_TEMP, CITATION } from "./components/testData";
import {
  applyChoice,
  catalogueFacts,
  discoveryStatusText,
  draftFromAiProposal,
  draftWithSuggestion,
  missingText,
  proposalIsReady,
  proposalSummary,
  shownSuggestions,
  toDiscoveryDraft,
} from "./discovery";

const SINGAPORE: PlaceCandidate = { name: "Singapore", country: "SG", lat: 1.29, lon: 103.85, kind: "city" };
const HELSINKI_DRAFT: CaseDraft = {
  variable: "precip",
  places: [{ lat: 60.17, lon: 24.94, name: "Helsinki" }],
  from: 1990,
  to: 2020,
  season: "JJA",
};

function proposal(overrides: Partial<Proposal> = {}): Proposal {
  return {
    variables: [AIR_TEMP],
    places: [SINGAPORE],
    from: 1981,
    to: 2025,
    season: "annual",
    notices: [],
    written_by_ai: true,
    ...overrides,
  };
}

function suggestion(id: string): VariableSuggestion {
  return {
    variable: { ...AIR_TEMP, id, name: id },
    reason: "Relevant here.",
    citations: [CITATION],
  };
}

function response(overrides: Partial<DiscoveryResponse> = {}): DiscoveryResponse {
  return {
    status: "ready",
    suggestions: [suggestion("air_temp")],
    proposal: proposal(),
    missing: [],
    clarification: null,
    notices: [],
    written_by_ai: true,
    corpus_version: "v1",
    ...overrides,
  };
}

describe("toDiscoveryDraft", () => {
  test("sends the settings as typed, with null for an open period", () => {
    expect(toDiscoveryDraft(EMPTY_DRAFT)).toEqual({
      variable: null,
      places: [],
      from: null,
      to: null,
      season: "annual",
    });
  });

  test("sends each place's point and label", () => {
    expect(toDiscoveryDraft(HELSINKI_DRAFT)).toEqual({
      variable: "precip",
      places: [{ lat: 60.17, lon: 24.94, name: "Helsinki" }],
      from: 1990,
      to: 2020,
      season: "JJA",
    });
  });

  test("sends a point without a label as a null name", () => {
    const draft = { ...EMPTY_DRAFT, places: [{ lat: 1, lon: 2 }] };
    expect(toDiscoveryDraft(draft).places).toEqual([{ lat: 1, lon: 2, name: null }]);
  });
});

describe("applyChoice", () => {
  test("sets the variable a choice names and keeps the rest", () => {
    expect(applyChoice(HELSINKI_DRAFT, { label: "Rain", variable: "air_temp" })).toEqual({
      ...HELSINKI_DRAFT,
      variable: "air_temp",
    });
  });

  test("replaces the places with the one place a choice names", () => {
    const next = applyChoice(HELSINKI_DRAFT, { label: "Singapore", place: SINGAPORE });
    expect(next.places).toEqual([{ lat: 1.29, lon: 103.85, name: "Singapore" }]);
    expect(next.variable).toBe("precip");
  });

  test("sets the years and months a choice names", () => {
    expect(applyChoice(EMPTY_DRAFT, { label: "Summer", from: 2000, to: 2010, season: "DJF" })).toEqual({
      ...EMPTY_DRAFT,
      from: 2000,
      to: 2010,
      season: "DJF",
    });
  });

  test("leaves the draft as it was for parts a choice sets to null", () => {
    const choice = { label: "Keep", variable: null, place: null, from: null, to: null, season: null };
    expect(applyChoice(HELSINKI_DRAFT, choice)).toEqual(HELSINKI_DRAFT);
  });

  test("does not change the draft it was given", () => {
    applyChoice(HELSINKI_DRAFT, { label: "Rain", variable: "air_temp" });
    expect(HELSINKI_DRAFT.variable).toBe("precip");
  });
});

describe("draftFromAiProposal", () => {
  test("takes the proposal's first variable, places, years and months", () => {
    expect(draftFromAiProposal(HELSINKI_DRAFT, proposal())).toEqual({
      variable: "air_temp",
      places: [{ lat: 1.29, lon: 103.85, name: "Singapore" }],
      from: 1981,
      to: 2025,
      season: "annual",
    });
  });

  test("keeps the settings' variable, places and years where the proposal leaves them open", () => {
    const next = draftFromAiProposal(
      HELSINKI_DRAFT,
      proposal({ variables: [], places: [], from: null, to: null, season: "JJA" }),
    );
    expect(next).toEqual(HELSINKI_DRAFT);
  });
});

describe("proposalIsReady", () => {
  test("offers to run a whole case the proposal named", () => {
    const next = draftFromAiProposal(EMPTY_DRAFT, proposal());
    expect(proposalIsReady(proposal(), next)).toBe(true);
  });

  test("does not offer to run places kept from the open case", () => {
    const empty = proposal({ places: [] });
    expect(proposalIsReady(empty, draftFromAiProposal(HELSINKI_DRAFT, empty))).toBe(false);
  });

  test("does not offer to run a proposal without a variable", () => {
    const empty = proposal({ variables: [] });
    expect(proposalIsReady(empty, draftFromAiProposal(EMPTY_DRAFT, empty))).toBe(false);
  });
});

describe("draftWithSuggestion", () => {
  test("uses the suggested variable with the answer's proposed places and years", () => {
    const answer = response({ suggestions: [suggestion("air_temp"), suggestion("precip")] });
    expect(draftWithSuggestion(EMPTY_DRAFT, answer, "precip")).toEqual({
      draft: {
        variable: "precip",
        places: [{ lat: 1.29, lon: 103.85, name: "Singapore" }],
        from: 1981,
        to: 2025,
        season: "annual",
      },
      ready: true,
    });
  });

  test("sets only the variable when the answer proposes no settings, and offers nothing to run", () => {
    const answer = response({ status: "clarify", proposal: null });
    expect(draftWithSuggestion(HELSINKI_DRAFT, answer, "air_temp")).toEqual({
      draft: { ...HELSINKI_DRAFT, variable: "air_temp" },
      ready: false,
    });
  });

  test("offers nothing to run when the proposal named no place", () => {
    const answer = response({ proposal: proposal({ places: [] }) });
    expect(draftWithSuggestion(HELSINKI_DRAFT, answer, "air_temp").ready).toBe(false);
  });
});

describe("shownSuggestions", () => {
  test("shows at most three suggestions", () => {
    const answer = response({ suggestions: ["a", "b", "c", "d"].map(suggestion) });
    expect(shownSuggestions(answer).map((item) => item.variable.id)).toEqual(["a", "b", "c"]);
  });
});

describe("missingText", () => {
  test("says nothing when nothing is missing", () => {
    expect(missingText([], null)).toBeNull();
  });

  test("names what is still to choose", () => {
    expect(missingText(["place", "from"], null)).toBe(
      "Still to choose in the case settings: the place and the first year.",
    );
  });

  test("says the settings hold the proposal's defaults for what the question left open", () => {
    expect(missingText(["from", "to"], proposal())).toBe(
      "Your question left open the first year and the last year, so the settings hold the proposed defaults. Check them before you run the case.",
    );
  });

  test("says a place the proposal does not fill is still to choose", () => {
    expect(missingText(["place"], proposal({ places: [] }))).toBe(
      "Still to choose in the case settings: the place.",
    );
  });

  test("splits what the proposal filled from what is still to choose", () => {
    expect(missingText(["place", "from"], proposal({ places: [] }))).toBe(
      "Your question left open the first year, so the settings hold the proposed defaults. Check them before you run the case. Still to choose in the case settings: the place.",
    );
  });

  test("says a variable the proposal does not name is still to choose", () => {
    expect(missingText(["variable"], proposal({ variables: [] }))).toBe(
      "Still to choose in the case settings: the variable.",
    );
  });
});

describe("catalogueFacts", () => {
  test("gives the definition and when the record starts", () => {
    expect(catalogueFacts(AIR_TEMP)).toEqual([AIR_TEMP.definition, "The record starts in 1981."]);
  });

  test("adds the variable's note and its source changes", () => {
    const variable = { ...AIR_TEMP, trend_note: "The source changed.", source_changes: [2001] };
    expect(catalogueFacts(variable)).toEqual([
      AIR_TEMP.definition,
      "The record starts in 1981.",
      "Note: The source changed.",
      "The data source for this variable changes in 2001, which can create an artificial step.",
    ]);
  });
});

describe("discoveryStatusText", () => {
  test("says the proposal is in the settings", () => {
    expect(discoveryStatusText(response())).toBe(
      "The AI's proposal is in the case settings. Check it, then select Run this case to confirm.",
    );
  });

  test("says suggestions wait when there is no proposal", () => {
    expect(discoveryStatusText(response({ proposal: null }))).toBe(
      "The AI's suggestions are below. Use one to put it in the case settings.",
    );
  });

  test("says a clarification waits", () => {
    expect(discoveryStatusText(response({ status: "clarify", proposal: null }))).toBe(
      "The AI needs one more detail. Pick an answer below, or set up the case by hand.",
    );
  });

  test("says there is no suggestion", () => {
    expect(discoveryStatusText(response({ status: "unsupported", suggestions: [], proposal: null }))).toBe(
      "No suggestion; you can set up the case by hand.",
    );
  });
});

describe("proposalSummary", () => {
  test("writes a whole proposal as the ready card writes a case", () => {
    expect(proposalSummary(proposal())).toBe("Air temperature · Singapore · 1981 to 2025, all months");
  });

  test("says which parts keep the settings' own", () => {
    expect(
      proposalSummary(proposal({ variables: [], places: [], from: null, to: null, season: "JJA" })),
    ).toBe("the same variable · the same places · the same period, June to August");
  });

  test("writes an open-ended period", () => {
    expect(proposalSummary(proposal({ to: null }))).toBe(
      "Air temperature · Singapore · from 1981, all months",
    );
    expect(proposalSummary(proposal({ from: null }))).toBe(
      "Air temperature · Singapore · to 2025, all months",
    );
  });
});
