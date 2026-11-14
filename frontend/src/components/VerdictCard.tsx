import type { JSX } from "react";
import type { Investigation, PlaceResult, Verdict, VariableSummary } from "../api";
import { cautionText } from "../cautions";
import { MORE_YEARS_NOTE, SIGNIFICANCE_DEFINITION } from "../definitions";
import { formatSignedRate, splitSign } from "../format";
import { FileTab } from "./FileTab";
import { ShapeSwatch } from "./ShapeSwatch";

interface VerdictCardProps {
  investigation: Investigation;
}

/**
 * The answer in words, as the first sheet of the case file, under its tab: for a comparison the
 * summary sentence first, then each place's verdict sentence with its stamp and its most
 * important caution (spec 3). Sentences come from the API as they are. The caller places it in a
 * live region that is in the page before it.
 */
export function VerdictCard({ investigation }: VerdictCardProps): JSX.Element {
  const { results, summary, variable } = investigation;
  return (
    <section className="panel verdict-card" aria-labelledby="verdict-heading">
      <FileTab label="Case file" />
      <h2 id="verdict-heading">Verdict</h2>
      {summary ? <p className="verdict-summary">{summary}</p> : null}
      <ul className="verdict-list">
        {results.map((result, index) => (
          <li key={index} className="verdict-place">
            <PlaceVerdict result={result} index={index} variable={variable} showName={results.length > 1} />
          </li>
        ))}
      </ul>
    </section>
  );
}

interface PlaceVerdictProps {
  result: PlaceResult;
  index: number;
  variable: VariableSummary;
  showName: boolean;
}

/**
 * One place's verdict: its stamp, the rate of a significant trend as a key figure, the sentence,
 * a note and the first caution.
 */
export function PlaceVerdict({ result, index, variable, showName }: PlaceVerdictProps): JSX.Element {
  const { verdict, trend } = result;
  const [firstCaution] = verdict.cautions;
  const caution = firstCaution === undefined ? null : cautionText(firstCaution, variable, trend);
  // Only a significant trend gets the large figure: a rate that year-to-year variation alone
  // could produce is not to be read as the answer.
  const figure =
    verdict.kind === "significant" && trend !== null
      ? splitSign(formatSignedRate(trend.sen_slope, variable.decimals))
      : null;
  return (
    <>
      {showName ? (
        <h3 className="verdict-place-name">
          <ShapeSwatch index={index} /> {result.place.name}
        </h3>
      ) : null}
      <VerdictStamp verdict={verdict} />
      {figure !== null ? (
        <p className="verdict-figure">
          <span className="verdict-figure-number">
            {figure[0] !== "" ? <span className="verdict-figure-sign">{figure[0]}</span> : null}
            {figure[1]}
          </span>{" "}
          <span className="verdict-figure-units">
            {variable.rate_units === "" ? "per decade" : `${variable.rate_units} per decade`}
          </span>
        </p>
      ) : null}
      <p className="verdict-sentence">{verdict.sentence}</p>
      {verdict.kind === "significant" || verdict.kind === "not_significant" ? <SignificanceHelp /> : null}
      <VerdictNote verdict={verdict} />
      {caution !== null ? (
        <p className="caution">
          <strong>Caution:</strong> {caution}
        </p>
      ) : null}
    </>
  );
}

const KIND_LABELS: Readonly<Record<Verdict["kind"], string>> = {
  significant: "Significant",
  not_significant: "Not significant",
  too_few_years: "Too few years",
  no_data: "No data",
  inference_unavailable: "Significance unavailable",
};

/** A verdict's direction as the stamp prints it: an arrow, a word, and the word's own style. */
interface StampDirection {
  arrow: string;
  word: string;
  tone: "rising" | "falling" | "level";
}

function stampDirection(verdict: Verdict): StampDirection | null {
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
function stampInk(verdict: Verdict): "rising" | "falling" | "faded" {
  if (verdict.kind !== "significant" || verdict.direction === null) return "faded";
  return verdict.direction;
}

/**
 * The verdict's stamp: the direction as an arrow and a word, never by colour alone (spec 3),
 * over the kind of verdict.
 */
function VerdictStamp({ verdict }: { verdict: Verdict }): JSX.Element {
  const direction = stampDirection(verdict);
  const level = direction?.tone === "level" ? " stamp-level" : "";
  return (
    <p className={`stamp stamp-${stampInk(verdict)}${level}`}>
      {direction !== null ? (
        <>
          <span className="stamp-direction">
            <span aria-hidden="true">{direction.arrow}</span> {direction.word}
          </span>{" "}
        </>
      ) : null}
      <span className="stamp-kind">{KIND_LABELS[verdict.kind]}</span>
    </p>
  );
}

/** Spec 3: "significant" carries its short definition where it appears, one tap away. */
function SignificanceHelp(): JSX.Element {
  return (
    <details className="disclosure">
      <summary>What does “significant” mean?</summary>
      <p>{SIGNIFICANCE_DEFINITION.definition}</p>
    </details>
  );
}

function VerdictNote({ verdict }: { verdict: Verdict }): JSX.Element | null {
  if (verdict.kind === "not_significant") return <p className="verdict-note">{MORE_YEARS_NOTE}</p>;
  if (verdict.kind === "too_few_years") {
    return <p className="verdict-note">Choose a longer period, or another place or variable.</p>;
  }
  if (verdict.kind === "no_data") {
    return (
      <p className="verdict-note">
        This can happen when a land variable, such as soil wetness, is asked for over open ocean. Try another
        place or variable.
      </p>
    );
  }
  return null;
}
