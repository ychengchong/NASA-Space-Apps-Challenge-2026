/**
 * The question bar's keyword mode (spec 8, "When the AI is off"): the words of a question are run
 * through `search_variables` and `find_place`, and the user confirms the match in the case settings.
 *
 * Place names are looked up as single words and as runs of a few words, such as "Rio de Janeiro".
 * A lookup counts only when a place's name equals the words, ignoring case and accents, so "Is"
 * never turns into Istanbul.
 */

import type { PlaceCandidate, VariableSummary } from "./api";
import { MAX_PLACES } from "./caseUrl";

// The function words of backend/app/tools/variables.py, kept identical: a variable query made
// only of these would make the backend list every variable.
export const FUNCTION_WORDS: ReadonlySet<string> = new Set([
  "a",
  "an",
  "the",
  "and",
  "or",
  "but",
  "so",
  "than",
  "then",
  "as",
  "if",
  "not",
  "no",
  "of",
  "in",
  "on",
  "at",
  "to",
  "from",
  "by",
  "for",
  "with",
  "over",
  "under",
  "above",
  "below",
  "into",
  "about",
  "around",
  "near",
  "since",
  "during",
  "per",
  "each",
  "down",
  "is",
  "are",
  "was",
  "were",
  "be",
  "been",
  "being",
  "am",
  "do",
  "does",
  "did",
  "has",
  "have",
  "had",
  "will",
  "would",
  "can",
  "could",
  "should",
  "may",
  "might",
  "i",
  "me",
  "my",
  "we",
  "us",
  "our",
  "you",
  "your",
  "he",
  "his",
  "she",
  "her",
  "it",
  "its",
  "they",
  "them",
  "their",
  "this",
  "that",
  "these",
  "those",
  "there",
  "here",
  "what",
  "which",
  "who",
  "when",
  "where",
  "why",
  "how",
  "very",
  "much",
  "many",
  "more",
  "most",
  "less",
  "any",
  "some",
  "all",
  "get",
  "gets",
  "getting",
  "got",
  "become",
  "becomes",
  "becoming",
]);

// The longest run of words looked up as one place name, enough for "Rio de Janeiro".
export const MAX_PLACE_PHRASE_WORDS = 3;
// The most place lookups one question makes, so a long question cannot use up the API's
// per-address rate limit (spec 11, "Security and privacy").
export const MAX_PLACE_LOOKUPS = 16;
// A phrase never starts or ends with a single letter, such as the "s" of "Nairobi's".
const MIN_EDGE_WORD_LENGTH = 2;

const WORD = /[\p{L}\p{N}]+/gu;
const DIGITS = /^\p{N}+$/u;
const COMBINING_MARK = /\p{M}/gu;

export interface QuestionWord {
  /** The word in lower case without accents. */
  key: string;
  /** Where the word starts and ends in the question, as string offsets. */
  start: number;
  end: number;
}

export interface PlacePhrase {
  /** Index of the phrase's first and last word in the question, both included. */
  first: number;
  last: number;
  /** The phrase as typed, sent to the place search. */
  text: string;
  /** The phrase's words in lower case without accents, joined by single spaces. */
  key: string;
}

export interface PlaceMatch {
  phrase: PlacePhrase;
  candidate: PlaceCandidate;
}

/** What the question bar found in a question. */
export interface KeywordProposal {
  /** Matching variables, best first. */
  variables: VariableSummary[];
  /** Places named in the question, in the order the question names them. */
  places: PlaceCandidate[];
}

/** The calls the matcher makes; the app passes the API client, tests pass fakes. */
export interface KeywordLookups {
  findPlaces(query: string, signal: AbortSignal): Promise<PlaceCandidate[]>;
  searchVariables(query: string, signal: AbortSignal): Promise<VariableSummary[]>;
}

/** Text in lower case, without accents, as words joined by single spaces: "São Paulo" -> "sao paulo". */
export function nameKey(text: string): string {
  return wordKeys(text).join(" ");
}

function wordKeys(text: string): string[] {
  return [...text.matchAll(WORD)].map((match) => foldWord(match[0]));
}

function foldWord(word: string): string {
  return word.normalize("NFKD").replace(COMBINING_MARK, "").toLowerCase();
}

export function questionWords(question: string): QuestionWord[] {
  return [...question.matchAll(WORD)].map((match) => ({
    key: foldWord(match[0]),
    start: match.index,
    end: match.index + match[0].length,
  }));
}

function canEdgePhrase(word: QuestionWord): boolean {
  return !FUNCTION_WORDS.has(word.key) && !DIGITS.test(word.key) && word.key.length >= MIN_EDGE_WORD_LENGTH;
}

/**
 * The phrases worth looking up as place names: runs of one to three words that neither start nor
 * end with a function word, a number or a single letter. Shorter phrases come first, then earlier
 * ones; a repeated phrase appears once; at most MAX_PLACE_LOOKUPS phrases are returned.
 */
export function placePhrases(question: string, words: readonly QuestionWord[]): PlacePhrase[] {
  const phrases: PlacePhrase[] = [];
  const seen = new Set<string>();
  for (let length = 1; length <= MAX_PLACE_PHRASE_WORDS; length += 1) {
    for (let first = 0; first + length <= words.length; first += 1) {
      const last = first + length - 1;
      const firstWord = words[first];
      const lastWord = words[last];
      if (firstWord === undefined || lastWord === undefined) continue;
      if (!canEdgePhrase(firstWord) || !canEdgePhrase(lastWord)) continue;
      const key = words
        .slice(first, last + 1)
        .map((word) => word.key)
        .join(" ");
      if (seen.has(key)) continue;
      seen.add(key);
      phrases.push({ first, last, text: question.slice(firstWord.start, lastWord.end), key });
    }
  }
  return phrases.slice(0, MAX_PLACE_LOOKUPS);
}

/**
 * The places named in the question, from the search results of each phrase (keyed by
 * `PlacePhrase.key`). A phrase names a place only when a candidate's name equals the phrase,
 * ignoring case and accents; the first such candidate, the most populous, is taken. Longer
 * phrases win over the words inside them. Matches come back in question order, without
 * repeating a place, at most MAX_PLACES of them.
 */
export function pickPlaces(
  phrases: readonly PlacePhrase[],
  found: ReadonlyMap<string, readonly PlaceCandidate[]>,
): PlaceMatch[] {
  const longestFirst = [...phrases].sort(
    (a, b) => b.last - b.first - (a.last - a.first) || a.first - b.first,
  );
  const matches: PlaceMatch[] = [];
  for (const phrase of longestFirst) {
    if (matches.some((match) => overlaps(match.phrase, phrase))) continue;
    const candidate = found.get(phrase.key)?.find((place) => nameKey(place.name) === phrase.key);
    if (candidate === undefined) continue;
    if (
      matches.some((match) => match.candidate.lat === candidate.lat && match.candidate.lon === candidate.lon)
    ) {
      continue;
    }
    matches.push({ phrase, candidate });
  }
  return matches.sort((a, b) => a.phrase.first - b.phrase.first).slice(0, MAX_PLACES);
}

function overlaps(a: PlacePhrase, b: PlacePhrase): boolean {
  return a.first <= b.last && b.first <= a.last;
}

/**
 * The words to search the catalogue with: every word that is not part of a matched place name,
 * not a function word and not a number, in question order. Empty when none is left.
 */
export function variableQuery(words: readonly QuestionWord[], matches: readonly PlaceMatch[]): string {
  return words
    .filter((_, index) => !matches.some((match) => match.phrase.first <= index && index <= match.phrase.last))
    .filter((word) => !FUNCTION_WORDS.has(word.key) && !DIGITS.test(word.key))
    .map((word) => word.key)
    .join(" ");
}

/**
 * Finds a variable and up to four places in a question. Places are looked up first, so the
 * words of a place name are not also used to pick the variable. Rejects when a lookup fails,
 * including with the AbortError of `signal`.
 */
export async function matchQuestion(
  question: string,
  lookups: KeywordLookups,
  signal: AbortSignal,
): Promise<KeywordProposal> {
  const words = questionWords(question);
  const phrases = placePhrases(question, words);
  const results = await Promise.all(phrases.map((phrase) => lookups.findPlaces(phrase.text, signal)));
  const found = new Map(phrases.map((phrase, index) => [phrase.key, results[index] ?? []]));
  const matches = pickPlaces(phrases, found);

  const query = variableQuery(words, matches);
  const variables = query === "" ? [] : await lookups.searchVariables(query, signal);
  return { variables, places: matches.map((match) => match.candidate) };
}
