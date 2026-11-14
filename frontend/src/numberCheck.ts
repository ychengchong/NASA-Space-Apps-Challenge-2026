/**
 * Marks the numbers in the AI's text that the number check could not match (spec 8, "The number
 * check"). The check runs on the server; this module only finds where each listed number sits.
 */

// The typographic minus sign, kept as an escape so the source holds no look-alike of "-".
const MINUS_SIGN = "\u2212";

// The server's cap (`_MAX_EXPONENT_DIGITS`): a longer exponent is not read as one, so in
// "1e-9999" the check lists "9999" and the screen must find the same text.
const MAX_EXPONENT_DIGITS = 3;

// The number pattern of the server's check (backend/app/adapters/chat.py, `_NUMBER`), so the
// screen marks exactly the numbers the check listed. A number is an optional sign; digits with
// optional thousands separators and optional decimals, or decimals alone, as in ".5"; then an
// optional exponent of 1 to 3 digits, as in "2.5e-11" or "4e-2". Python's `\w` matches letters
// and digits of any script, written here as \p{L}\p{N}_. A number must not continue a word or
// another number, so "CO2" and "v2.10" hold none.
const NUMBER = new RegExp(
  `(?<![\\p{L}\\p{N}_.])[-+${MINUS_SIGN}]?` +
    `(?:(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\\.[0-9]+)?|\\.[0-9]+)` +
    `(?:[eE][-+${MINUS_SIGN}]?[0-9]{1,${MAX_EXPONENT_DIGITS}})?(?![0-9])`,
  "gu",
);

/** A piece of the AI's text; `unverified` marks a number the check could not match. */
export interface TextSpan {
  text: string;
  unverified: boolean;
}

/**
 * The text cut into spans, with each number listed in `unverified` (as the check wrote it, sign
 * and separators included) in a span of its own. Every occurrence of a listed number is marked.
 * The spans joined give back `text`.
 */
export function splitUnverified(text: string, unverified: readonly string[]): TextSpan[] {
  const listed = new Set(unverified);
  const spans: TextSpan[] = [];
  let plainStart = 0;
  if (listed.size > 0) {
    for (const match of text.matchAll(NUMBER)) {
      if (!listed.has(match[0])) continue;
      if (match.index > plainStart)
        spans.push({ text: text.slice(plainStart, match.index), unverified: false });
      spans.push({ text: match[0], unverified: true });
      plainStart = match.index + match[0].length;
    }
  }
  if (plainStart < text.length) spans.push({ text: text.slice(plainStart), unverified: false });
  return spans;
}
