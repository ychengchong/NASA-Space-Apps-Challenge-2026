/**
 * The record years of a place as the rows of a small table (spec 7, "Record years"). Every number
 * is an API field, written with the digits of the API's sentences. Where the fields cannot say
 * what a sentence says, such as years tied with the last one listed, the row keeps the sentence
 * as the API wrote it.
 */

import type { Records } from "./api";
import { formatRecordValue, formatSignedRate, withUnits } from "./format";

export interface RecordYear {
  year: number;
  value: string;
}

export type RecordRow =
  | { kind: "years"; label: "Highest" | "Lowest"; items: RecordYear[] }
  | { kind: "window"; label: string; last: string; first: string; change: string }
  | { kind: "sentence"; label: string; sentence: string };

interface Units {
  decimals: number;
  rate_units: string;
}

// The order of the API's record sentences: highest, lowest, then the window (verdict.py).
const HIGHEST_SENTENCE = 0;
const LOWEST_SENTENCE = 1;

export function recordRows(records: Records, variable: Units): RecordRow[] {
  const { highest, lowest, sentences } = records;
  if (highest.length === 0 && lowest.length === 0) {
    // Every year used has one value: the API says so in its one sentence.
    const sentence = sentences[0];
    return sentence === undefined ? [] : [{ kind: "sentence", label: "Every year", sentence }];
  }
  const rows: RecordRow[] = [
    yearsRow("Highest", records.highest, records.highest_tied, sentences[HIGHEST_SENTENCE], variable),
    yearsRow("Lowest", records.lowest, records.lowest_tied, sentences[LOWEST_SENTENCE], variable),
  ];
  const { first_ten: first, last_ten: last, change } = records;
  if (first !== null && last !== null && change !== null) {
    rows.push({
      kind: "window",
      label: "Ten-year means",
      last: `${span(last.years)}: ${formatRecordValue(last.mean, variable.decimals)}`,
      first: `${span(first.years)}: ${formatRecordValue(first.mean, variable.decimals)}`,
      change: withUnits(formatSignedRate(change, variable.decimals), variable.rate_units),
    });
  }
  return rows;
}

function yearsRow(
  label: "Highest" | "Lowest",
  listed: Records["highest"],
  tied: number,
  sentence: string | undefined,
  variable: Units,
): RecordRow {
  if (tied > 0 && sentence !== undefined) return { kind: "sentence", label, sentence };
  return {
    kind: "years",
    label,
    items: listed.map((item) => ({
      year: item.year,
      value: formatRecordValue(item.value, variable.decimals),
    })),
  };
}

/** The first and the last year of a window, as the sentences write them: "2016 to 2025". */
function span(years: readonly number[]): string {
  return `${years[0] ?? ""} to ${years.at(-1) ?? ""}`;
}
