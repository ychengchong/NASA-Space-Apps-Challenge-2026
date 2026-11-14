import type { JSX } from "react";
import type { Investigation, PlaceResult, Verdict, VariableSummary } from "../api";
import { cautionText } from "../cautions";
import { MORE_YEARS_NOTE, SIGNIFICANCE_DEFINITION } from "../definitions";
import { ShapeSwatch } from "./ShapeSwatch";

interface VerdictCardProps {
  investigation: Investigation;
}

/**
 * The answer in words: for a comparison the summary sentence first, then each place's verdict
 * sentence with its direction and its most important caution (spec 3). Sentences come from the
 * API as they are. The caller places it in a live region that is in the page before it.
 */
export function VerdictCard({ investigation }: VerdictCardProps): JSX.Element {
  const { results, summary, variable } = investigation;
  return (
    <section className="panel verdict-card" aria-labelledby="verdict-heading">
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

/** One place's verdict: its direction and kind, the sentence, a note and the first caution. */
export function PlaceVerdict({ result, index, variable, showName }: PlaceVerdictProps): JSX.Element {
  const { verdict, trend } = result;
  const [firstCaution] = verdict.cautions;
  const caution = firstCaution === undefined ? null : cautionText(firstCaution, variable, trend);
  return (
    <>
      {showName ? (
        <h3 className="verdict-place-name">
          <ShapeSwatch index={index} /> {result.place.name}
        </h3>
      ) : null}
      <VerdictBadges verdict={verdict} />
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

/** The direction as an arrow and a word, never by colour alone (spec 3), and the kind. */
function VerdictBadges({ verdict }: { verdict: Verdict }): JSX.Element {
  return (
    <p className="verdict-badges">
      <DirectionBadge verdict={verdict} />
      <span className={`badge badge-${verdict.kind}`}>{KIND_LABELS[verdict.kind]}</span>
    </p>
  );
}

function DirectionBadge({ verdict }: { verdict: Verdict }): JSX.Element | null {
  if (verdict.direction === "rising") return <Direction arrow="↑" word="Rising" />;
  if (verdict.direction === "falling") return <Direction arrow="↓" word="Falling" />;
  // Spec 7: a zero Sen's slope is a test with no direction.
  if (verdict.kind === "not_significant") return <Direction arrow="→" word="Zero estimated slope" />;
  return null;
}

function Direction({ arrow, word }: { arrow: string; word: string }): JSX.Element {
  return (
    <span className="badge badge-direction">
      <span aria-hidden="true" className="badge-arrow">
        {arrow}
      </span>{" "}
      {word}
    </span>
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
