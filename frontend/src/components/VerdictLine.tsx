import type { JSX } from "react";
import type { Investigation } from "../api";
import { verdictLine } from "../verdictStamp";
import { ShapeSwatch } from "./ShapeSwatch";

interface VerdictLineProps {
  investigation: Investigation;
  /** True once the verdict card has scrolled out of view above the top of the screen. */
  shown: boolean;
}

/**
 * The verdict in one line at the top of the case file, shown once the card has scrolled away, so
 * the answer stays in sight while the evidence is read (spec 3, "Verdict line"). It repeats the
 * card's figure and stamp words, so it is hidden from screen readers and holds nothing focusable.
 */
export function VerdictLine({ investigation, shown }: VerdictLineProps): JSX.Element {
  const showMarkers = investigation.results.length > 1;
  return (
    <div className="verdict-line-anchor">
      <p className={shown ? "verdict-line is-shown" : "verdict-line"} aria-hidden="true">
        {verdictLine(investigation).map((entry) => (
          <span key={entry.index} className="verdict-line-entry">
            {showMarkers ? <ShapeSwatch index={entry.index} /> : null}
            {entry.name !== null ? <span className="verdict-line-name">{entry.name}</span> : null}
            {entry.figure !== null ? <span className="verdict-line-figure">{entry.figure}</span> : null}
            <span className={`verdict-line-stamp stamp-${entry.ink}`}>
              {entry.direction !== null ? `${entry.direction.arrow} ${entry.direction.word} · ` : null}
              {entry.kind}
            </span>
          </span>
        ))}
      </p>
    </div>
  );
}
