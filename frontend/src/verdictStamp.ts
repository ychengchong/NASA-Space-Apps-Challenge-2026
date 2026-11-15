import type { Investigation, PlaceResult, Verdict, VariableSummary } from "./api";
import { formatRatePerDecade } from "./format";

/** The kind of verdict as the stamp prints it (spec 3). */
export const KIND_LABELS: Readonly<Record<Verdict["kind"], string>> = {
  significant: "Significant",
  not_significant: "Not significant",
  too_few_years: "Too few years",
  no_data: "No data",
  inference_unavailable: "Significance unavailable",
};

/** A verdict's direction as the stamp prints it: an arrow, a word, and the word's own style. */
export interface StampDirection {
  arrow: string;
  word: string;
  tone: "rising" | "falling" | "level";
}

export function stampDirection(verdict: Verdict): StampDirection | null {
  if (verdict.direction === "rising") return { arrow: "↑", word: "Rising", tone: "rising" };
  if (verdict.direction === "falling") return { arrow: "↓", word: "Falling", tone: "falling" };
  // Spec 7: a zero Sen's slope is a test with no direction.
  if (verdict.kind === "not_significant") {
    return { arrow: "→", word: "Zero estimated slope", tone: "level" };
  }
  return null;
}

/**
 * The ink of the stamp (spec 3): the red or the blue of the region map's scale for a significant
 * rise or fall, and a faded ink for every other verdict, whose direction the test did not settle.
 */
export function stampInk(verdict: Verdict): "rising" | "falling" | "faded" {
  if (verdict.kind !== "significant" || verdict.direction === null) return "faded";
  return verdict.direction;
}

/** The colour of the case file: the direction every place's verdict shares, if any. */
export type VerdictTone = "rising" | "falling" | "plain";

/**
 * The case file's colour (spec 3, "Verdict card"): rising or falling when every place's stamp is
 * in that ink, so only significant trends colour it; plain for anything else, mixed directions
 * included.
 */
export function verdictTone(investigation: Investigation): VerdictTone {
  const inks = investigation.results.map((result) => stampInk(result.verdict));
  if (inks.length === 0) return "plain";
  if (inks.every((ink) => ink === "rising")) return "rising";
  if (inks.every((ink) => ink === "falling")) return "falling";
  return "plain";
}

/**
 * The rate per decade the verdict card prints as its large figure, such as "+0.79 °C per decade",
 * or null. Only a significant trend gets the figure: a rate that year-to-year variation alone
 * could produce is not to be read as the answer (spec 3, "Verdict card").
 */
export function verdictFigure(result: PlaceResult, variable: VariableSummary): string | null {
  if (result.verdict.kind !== "significant" || result.trend === null) return null;
  return formatRatePerDecade(result.trend.sen_slope, variable);
}

/** One place's entry in the verdict line: words and figures taken from the verdict card. */
export interface VerdictLineEntry {
  /** The place's position in the case, which picks its marker shape. */
  index: number;
  /** The place's name, or null when the line shows one place's figure instead. */
  name: string | null;
  figure: string | null;
  direction: StampDirection | null;
  kind: string;
  ink: "rising" | "falling" | "faded";
}

/**
 * What the one-line verdict holds once the card has scrolled out of view (spec 3, "Verdict
 * line"): for each place the card's figure, if it has one, and the words of its stamp. One place
 * with a figure needs no name; a place without a figure is named, and in a comparison every place
 * is named, so each entry says which answer it repeats.
 */
export function verdictLine(investigation: Investigation): VerdictLineEntry[] {
  const { results, variable } = investigation;
  const comparison = results.length > 1;
  return results.map((result, index) => {
    const figure = verdictFigure(result, variable);
    return {
      index,
      name: comparison || figure === null ? result.place.name : null,
      figure,
      direction: stampDirection(result.verdict),
      kind: KIND_LABELS[result.verdict.kind],
      ink: stampInk(result.verdict),
    };
  });
}
