import type { JSX } from "react";
import type { VariableSummary } from "../api";
import { DEFINITIONS } from "../definitions";

/** The definitions of spec 7 and the variable's own, for an evidence panel (spec 2 and 3). */
export function WordsUsedHere({ variable }: { variable: VariableSummary }): JSX.Element {
  return (
    <>
      <h3>Words used here</h3>
      <dl className="definitions">
        {DEFINITIONS.map((item) => (
          <div key={item.term}>
            <dt>{item.term}</dt>
            <dd>{item.definition}</dd>
          </div>
        ))}
        <div>
          <dt>{variable.name}</dt>
          <dd>
            {variable.definition} Units: {variable.units}.
          </dd>
        </div>
      </dl>
    </>
  );
}
