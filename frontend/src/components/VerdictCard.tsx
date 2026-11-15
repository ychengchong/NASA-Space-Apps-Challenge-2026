import type { JSX } from "react";
import type { Investigation, PlaceResult, Verdict, VariableSummary } from "../api";
import { cautionText } from "../cautions";
import { MORE_YEARS_NOTE, SIGNIFICANCE_DEFINITION } from "../definitions";
import { formatSignedRate, splitSign } from "../format";
import { KIND_LABELS, stampDirection, stampInk, verdictLine } from "../verdictStamp";
import { FileTab } from "./FileTab";
import { ShapeSwatch } from "./ShapeSwatch";

interface VerdictCardProps {
  investigation: Investigation;
}

/**
 * The answer in words, as the first sheet of the case file, under its tab (spec 3). One place
 * gets its verdict in full: the stamp, the sentence and the most important caution. A comparison
 * gets the summary sentence, then each place at a glance, and the full verdicts behind one fold,
 * so the card stays short enough for the chart to follow it closely. Sentences come from the API
 * as they are. The caller places it in a live region that is in the page before it.
 */
export function VerdictCard({ investigation }: VerdictCardProps): JSX.Element {
  const { results, summary, variable } = investigation;
  const comparison = results.length > 1;
  const full = (
    <>
      {investigation.gap ? <p className="verdict-note">{investigation.gap.sentence}</p> : null}
      <ul className="verdict-list">
        {results.map((result, index) => (
          <li key={index} className="verdict-place">
            <PlaceVerdict result={result} index={index} variable={variable} showName={comparison} />
          </li>
        ))}
      </ul>
    </>
  );
  return (
    <section className="panel verdict-card" aria-labelledby="verdict-heading">
      <FileTab label="Case file" />
      <h2 id="verdict-heading">Verdict</h2>
      {summary ? <p className="verdict-summary">{summary}</p> : null}
      {comparison ? (
        <>
          <VerdictGlance investigation={investigation} />
          <details className="disclosure verdict-full">
            <summary>Read each place’s full verdict and cautions</summary>
            {full}
          </details>
        </>
      ) : (
        full
      )}
    </section>
  );
}

/**
 * Each place of a comparison in one row: its marker, its name, the card's figure if it has one,
 * and the words of its stamp. It repeats nothing but what the full verdicts hold.
 */
function VerdictGlance({ investigation }: VerdictCardProps): JSX.Element {
  return (
    <ul className="verdict-glance">
      {verdictLine(investigation).map((entry) => (
        <li key={entry.index}>
          <ShapeSwatch index={entry.index} />
          <span className="verdict-glance-name">{entry.name}</span>
          {entry.figure !== null ? <span className="verdict-glance-figure">{entry.figure}</span> : null}
          <span className={`verdict-line-stamp stamp-${entry.ink}`}>
            {entry.direction !== null ? (
              <>
                <span aria-hidden="true">{entry.direction.arrow}</span> {entry.direction.word} ·{" "}
              </>
            ) : null}
            {entry.kind}
          </span>
        </li>
      ))}
    </ul>
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
