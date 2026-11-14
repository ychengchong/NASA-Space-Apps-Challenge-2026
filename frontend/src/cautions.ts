/**
 * The text a user reads for each caution (spec 7, "Cautions"). The API sends caution codes only;
 * the words below are the spec's, word for word.
 */

import type { Caution, Trend, VariableSummary } from "./api";

type FixedCaution = Exclude<Caution, "source_change" | "variable_note">;

const FIXED_CAUTION_TEXTS: Readonly<Record<FixedCaution, string>> = {
  short_record: "This record is short. Trends in short records often fade as more years arrive.",
  autocorrelated:
    "Year-to-year dependence is present. Check the stated assumptions; other dependence may invalidate inference.",
  methods_disagree: "Two standard methods disagree about this trend.",
  borderline: "This result is close to the threshold for significance.",
};

function sourceChangeText(years: readonly number[]): string {
  const yearList = joinWords(years.map(String));
  return `The data source for this variable changes in ${yearList}, which can create an artificial step.`;
}

/**
 * The years in `variable.source_changes` that the trend's years cross. Spec 7: the first year used
 * is before the change year and the last year used is on or after it.
 */
export function crossedSourceChanges(
  variable: VariableSummary,
  trend: Pick<Trend, "first_year" | "last_year">,
): number[] {
  const changes = variable.source_changes ?? [];
  return changes.filter((year) => trend.first_year < year && year <= trend.last_year);
}

/**
 * The text for one caution, or null when there is nothing to write: a `variable_note` for a
 * variable without a note, or a `source_change` for a variable that lists no change year.
 * A `source_change` names the crossed years; without a trend it names every listed change year.
 */
export function cautionText(caution: Caution, variable: VariableSummary, trend: Trend | null): string | null {
  if (caution === "variable_note") return variable.trend_note ?? null;
  if (caution === "source_change") {
    const crossed = trend === null ? [] : crossedSourceChanges(variable, trend);
    const years = crossed.length > 0 ? crossed : (variable.source_changes ?? []);
    return years.length > 0 ? sourceChangeText(years) : null;
  }
  return FIXED_CAUTION_TEXTS[caution];
}

/** The texts of `cautions`, in the order given (most important first), skipping any without text. */
export function cautionTexts(
  cautions: readonly Caution[],
  variable: VariableSummary,
  trend: Trend | null,
): string[] {
  return cautions.flatMap((caution) => cautionText(caution, variable, trend) ?? []);
}

/** Words joined as "A", "A and B" or "A, B and C", as the backend joins them. */
export function joinWords(words: readonly string[]): string {
  if (words.length <= 1) return words[0] ?? "";
  return `${words.slice(0, -1).join(", ")} and ${words.at(-1) ?? ""}`;
}
