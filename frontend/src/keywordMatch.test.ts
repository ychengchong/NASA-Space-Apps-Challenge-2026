import { describe, expect, test } from "vitest";
// The backend's search tool, as text, to compare its function words with this module's.
import backendVariablesSource from "../../backend/app/tools/variables.py?raw";
import type { PlaceCandidate, VariableSummary } from "./api";
import {
  FUNCTION_WORDS,
  matchQuestion,
  MAX_PLACE_LOOKUPS,
  nameKey,
  pickPlaces,
  placePhrases,
  questionWords,
  variableQuery,
} from "./keywordMatch";
import type { KeywordLookups } from "./keywordMatch";

function city(name: string, lat = 0, lon = 0): PlaceCandidate {
  return { name, lat, lon, kind: "city" };
}

const PLACES: PlaceCandidate[] = [
  city("Istanbul", 41.01, 28.95),
  city("Nairobi", -1.28, 36.82),
  city("Naivasha", -0.71, 36.43),
  city("Rio", 38.25, 21.79),
  city("Rio de Janeiro", -22.91, -43.18),
  city("São Paulo", -23.55, -46.64),
  city("Madrid", 40.42, -3.7),
  city("Helsinki", 60.17, 24.94),
  city("Lagos", 6.45, 3.39),
  city("Paris", 48.85, 2.35),
  city("Saint-Denis", 48.94, 2.36),
];

const AIR_TEMPERATURE = { id: "air_temp", name: "Air temperature" } as VariableSummary;

/** Searches PLACES like find_place: names containing the query, exact matches first. */
function fakeLookups(): KeywordLookups & { placeQueries: string[]; variableQueries: string[] } {
  const placeQueries: string[] = [];
  const variableQueries: string[] = [];
  return {
    placeQueries,
    variableQueries,
    findPlaces(query) {
      placeQueries.push(query);
      const key = nameKey(query);
      const found = PLACES.filter((place) => nameKey(place.name).includes(key));
      found.sort((a, b) => Number(nameKey(b.name) === key) - Number(nameKey(a.name) === key));
      return Promise.resolve(found.slice(0, 5));
    },
    searchVariables(query) {
      variableQueries.push(query);
      return Promise.resolve(query.includes("warmer") ? [AIR_TEMPERATURE] : []);
    },
  };
}

/** The quoted words of the `FUNCTION_WORDS = frozenset(...)` block of variables.py. */
function backendFunctionWords(source: string): string[] {
  const block = /^FUNCTION_WORDS = frozenset\(([\s\S]*?)^\)/m.exec(source)?.[1];
  if (block === undefined) throw new Error("variables.py has no FUNCTION_WORDS block.");
  return [...block.matchAll(/"([^"]*)"/g)].map((match) => match[1] ?? "");
}

function phraseKeys(question: string): string[] {
  return placePhrases(question, questionWords(question)).map((phrase) => phrase.key);
}

describe("FUNCTION_WORDS", () => {
  test("holds exactly the function words of the backend's variable search", () => {
    const backendWords = backendFunctionWords(backendVariablesSource);
    expect(backendWords.length).toBeGreaterThan(0);
    expect([...FUNCTION_WORDS].sort()).toEqual([...new Set(backendWords)].sort());
  });
});

describe("questionWords", () => {
  test("splits a question into words, in lower case and without accents", () => {
    expect(questionWords("Is São Paulo wetter?").map((word) => word.key)).toEqual([
      "is",
      "sao",
      "paulo",
      "wetter",
    ]);
  });

  test("keeps where each word sits in the question", () => {
    const [, nairobi] = questionWords("Is Nairobi warmer?");
    expect(nairobi).toEqual({ key: "nairobi", start: 3, end: 10 });
  });
});

describe("placePhrases", () => {
  test("looks up single words and runs of words, never starting or ending with a function word", () => {
    expect(phraseKeys("Is Nairobi getting warmer?")).toEqual(["nairobi", "warmer", "nairobi getting warmer"]);
  });

  test("skips function words and numbers", () => {
    expect(phraseKeys("Is it getting warmer since 1990?")).toEqual(["warmer"]);
  });

  test("looks up a three-word name", () => {
    expect(phraseKeys("Is Rio de Janeiro wetter?")).toContain("rio de janeiro");
  });

  test("sends the phrase as it was typed", () => {
    const question = "Is Saint-Denis wetter?";
    const phrase = placePhrases(question, questionWords(question)).find(
      (found) => found.key === "saint denis",
    );
    expect(phrase?.text).toBe("Saint-Denis");
  });

  test("looks up a repeated phrase once", () => {
    expect(phraseKeys("Paris or Paris?")).toEqual(["paris", "paris or paris"]);
  });

  test("makes a limited number of lookups for a long question", () => {
    const question = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike";
    expect(placePhrases(question, questionWords(question))).toHaveLength(MAX_PLACE_LOOKUPS);
  });
});

describe("pickPlaces", () => {
  test("ignores a place whose name only starts with the words", () => {
    const question = "Is Nairobi getting warmer?";
    const phrases = placePhrases(question, questionWords(question));
    const found = new Map([
      ["nairobi", [city("Nairobi")]],
      ["warmer", [city("Warmerdam")]],
    ]);
    expect(pickPlaces(phrases, found).map((match) => match.candidate.name)).toEqual(["Nairobi"]);
  });

  test("takes the first candidate whose name equals the words", () => {
    const question = "London";
    const phrases = placePhrases(question, questionWords(question));
    const found = new Map([["london", [city("East London"), city("London", 51.5), city("London", 43)]]]);
    expect(pickPlaces(phrases, found)[0]?.candidate.lat).toBe(51.5);
  });
});

describe("variableQuery", () => {
  test("leaves out the words of a matched place, function words and numbers", () => {
    const question = "Is Nairobi getting warmer since 1990?";
    const words = questionWords(question);
    const phrases = placePhrases(question, words);
    const matches = pickPlaces(phrases, new Map([["nairobi", [city("Nairobi")]]]));
    expect(variableQuery(words, matches)).toBe("warmer");
  });
});

describe("matchQuestion", () => {
  const signal = new AbortController().signal;

  test("finds air temperature and Nairobi in a plain question", async () => {
    const proposal = await matchQuestion("Is Nairobi getting warmer?", fakeLookups(), signal);
    expect(proposal.variables.map((variable) => variable.id)).toEqual(["air_temp"]);
    expect(proposal.places.map((place) => place.name)).toEqual(["Nairobi"]);
  });

  test("does not turn the word 'Is' into Istanbul", async () => {
    const proposal = await matchQuestion("Is it getting warmer?", fakeLookups(), signal);
    expect(proposal.places).toEqual([]);
  });

  test("prefers a longer name over a shorter name inside it", async () => {
    const proposal = await matchQuestion("Is Rio de Janeiro getting wetter?", fakeLookups(), signal);
    expect(proposal.places.map((place) => place.name)).toEqual(["Rio de Janeiro"]);
  });

  test("matches a name typed without its accents", async () => {
    const proposal = await matchQuestion("Is Sao Paulo getting wetter?", fakeLookups(), signal);
    expect(proposal.places.map((place) => place.name)).toEqual(["São Paulo"]);
  });

  test("keeps places in the order the question names them", async () => {
    const proposal = await matchQuestion("Compare Madrid, Helsinki and Lagos", fakeLookups(), signal);
    expect(proposal.places.map((place) => place.name)).toEqual(["Madrid", "Helsinki", "Lagos"]);
  });

  test("keeps at most four places", async () => {
    const proposal = await matchQuestion("Madrid Helsinki Lagos Paris Nairobi", fakeLookups(), signal);
    expect(proposal.places.map((place) => place.name)).toEqual(["Madrid", "Helsinki", "Lagos", "Paris"]);
  });

  test("names a place given twice only once", async () => {
    const proposal = await matchQuestion("Is Paris warmer than Paris?", fakeLookups(), signal);
    expect(proposal.places.map((place) => place.name)).toEqual(["Paris"]);
  });

  test("searches the variables without the words of the place name", async () => {
    const lookups = fakeLookups();
    await matchQuestion("Is Nairobi getting warmer?", lookups, signal);
    expect(lookups.variableQueries).toEqual(["warmer"]);
  });

  test("does not search the variables when only a place is named", async () => {
    const lookups = fakeLookups();
    const proposal = await matchQuestion("Helsinki?", lookups, signal);
    expect(lookups.variableQueries).toEqual([]);
    expect(proposal.variables).toEqual([]);
  });

  test("makes no lookup for a question of function words only", async () => {
    const lookups = fakeLookups();
    await matchQuestion("Is it?", lookups, signal);
    expect(lookups.placeQueries).toEqual([]);
    expect(lookups.variableQueries).toEqual([]);
  });

  test("rejects when a lookup fails", async () => {
    const lookups: KeywordLookups = {
      findPlaces: () => Promise.reject(new Error("offline")),
      searchVariables: () => Promise.resolve([]),
    };
    await expect(matchQuestion("Is Nairobi warmer?", lookups, signal)).rejects.toThrow("offline");
  });
});
