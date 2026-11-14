import { describe, expect, test } from "vitest";
import type { PlaceCandidate, VariableSummary } from "./api";
import {
  applyPlaceAction,
  caseFromDraft,
  draftFromCase,
  draftFromProposal,
  EMPTY_DRAFT,
  parseYearText,
  placeActions,
  placeFromCandidate,
  removePlace,
  samePoint,
} from "./caseDraft";
import type { CaseDraft } from "./caseDraft";
import type { CaseParams } from "./caseUrl";

const HELSINKI = { lat: 60.17, lon: 24.94, name: "Helsinki" };
const NAIROBI = { lat: -1.28, lon: 36.82, name: "Nairobi" };
const MADRID = { lat: 40.42, lon: -3.7, name: "Madrid" };
const LAGOS = { lat: 6.45, lon: 3.39, name: "Lagos" };
const PARIS = { lat: 48.85, lon: 2.35, name: "Paris" };

const HELSINKI_CASE: CaseParams = {
  variable: "air_temp",
  places: [HELSINKI],
  from: 1981,
  to: 2025,
  season: "annual",
};

describe("draftFromCase and caseFromDraft", () => {
  test("turn an open case into a draft and back", () => {
    expect(caseFromDraft(draftFromCase(HELSINKI_CASE))).toEqual(HELSINKI_CASE);
  });

  test("leave the scan out of the draft", () => {
    expect(draftFromCase({ ...HELSINKI_CASE, scan: true })).not.toHaveProperty("scan");
  });

  test("leave out years the draft does not set", () => {
    const draft: CaseDraft = { variable: "air_temp", places: [HELSINKI], season: "JJA" };
    expect(caseFromDraft(draft)).toEqual({ variable: "air_temp", places: [HELSINKI], season: "JJA" });
  });

  test("give no case without a variable", () => {
    expect(caseFromDraft({ ...EMPTY_DRAFT, places: [HELSINKI] })).toBeNull();
  });

  test("give no case without a place", () => {
    expect(caseFromDraft({ ...EMPTY_DRAFT, variable: "air_temp" })).toBeNull();
  });
});

describe("placeActions", () => {
  test("offers to use the first place", () => {
    expect(placeActions([], HELSINKI)).toEqual(["use"]);
  });

  test("offers to replace or compare with a single place", () => {
    expect(placeActions([HELSINKI], NAIROBI)).toEqual(["replace", "compare"]);
  });

  test("offers to add to a comparison", () => {
    expect(placeActions([HELSINKI, NAIROBI], MADRID)).toEqual(["add"]);
  });

  test("offers nothing once the case holds four places", () => {
    expect(placeActions([HELSINKI, NAIROBI, MADRID, LAGOS], PARIS)).toEqual([]);
  });

  test("offers nothing for a place already in the case", () => {
    expect(placeActions([HELSINKI], { lat: 60.171, lon: 24.938 })).toEqual([]);
  });
});

describe("applyPlaceAction and removePlace", () => {
  const draft: CaseDraft = { ...EMPTY_DRAFT, variable: "air_temp", places: [HELSINKI] };

  test("replace swaps the only place", () => {
    expect(applyPlaceAction(draft, "replace", NAIROBI).places).toEqual([NAIROBI]);
  });

  test("compare adds a second place after the first", () => {
    expect(applyPlaceAction(draft, "compare", NAIROBI).places).toEqual([HELSINKI, NAIROBI]);
  });

  test("removePlace drops the place at the index", () => {
    expect(removePlace({ ...draft, places: [HELSINKI, NAIROBI] }, 0).places).toEqual([NAIROBI]);
  });
});

describe("samePoint", () => {
  test("treats points with the same link coordinates as one place", () => {
    expect(samePoint({ lat: 60.1701, lon: 24.9449 }, { lat: 60.17, lon: 24.94 })).toBe(true);
  });

  test("rounds an exact tie as the backend's link does", () => {
    expect(samePoint({ lat: 9.56, lon: 44.065 }, { lat: 9.56, lon: 44.06 })).toBe(true);
    expect(samePoint({ lat: 9.56, lon: 44.065 }, { lat: 9.56, lon: 44.07 })).toBe(false);
  });

  test("tells apart points whose link coordinates differ", () => {
    expect(samePoint({ lat: 60.17, lon: 24.94 }, { lat: 60.18, lon: 24.94 })).toBe(false);
  });
});

describe("placeFromCandidate", () => {
  test("labels the place with its name", () => {
    const candidate: PlaceCandidate = {
      name: "Nairobi",
      country: "Kenya",
      lat: -1.2833,
      lon: 36.8167,
      kind: "city",
    };
    expect(placeFromCandidate(candidate)).toEqual({ lat: -1.2833, lon: 36.8167, name: "Nairobi" });
  });

  test("cuts a long name to the 40-character label limit", () => {
    const candidate: PlaceCandidate = { name: "x".repeat(45), lat: 0, lon: 0, kind: "city" };
    expect(placeFromCandidate(candidate).name).toHaveLength(40);
  });
});

describe("draftFromProposal", () => {
  const airTemperature = { id: "air_temp" } as VariableSummary;
  const precipitation = { id: "precipitation" } as VariableSummary;
  const nairobi: PlaceCandidate = { name: "Nairobi", lat: -1.2833, lon: 36.8167, kind: "city" };

  test("takes the best variable and the places found", () => {
    const draft = draftFromProposal(EMPTY_DRAFT, {
      variables: [airTemperature, precipitation],
      places: [nairobi],
    });
    expect(draft).toEqual({ ...EMPTY_DRAFT, variable: "air_temp", places: [placeFromCandidate(nairobi)] });
  });

  test("keeps the open case's places when the question names none", () => {
    const base = draftFromCase(HELSINKI_CASE);
    const draft = draftFromProposal(base, { variables: [precipitation], places: [] });
    expect(draft).toEqual({ ...base, variable: "precipitation" });
  });

  test("keeps the open case's variable when the question names none", () => {
    const base = draftFromCase(HELSINKI_CASE);
    expect(draftFromProposal(base, { variables: [], places: [nairobi] }).variable).toBe("air_temp");
  });
});

describe("parseYearText", () => {
  test("reads a four-digit year", () => {
    expect(parseYearText(" 1990 ")).toBe(1990);
  });

  test("reads an empty box as the full record", () => {
    expect(parseYearText("")).toBeUndefined();
  });

  test("rejects anything else", () => {
    expect(parseYearText("90")).toBe("invalid");
    expect(parseYearText("1990.5")).toBe("invalid");
  });
});
