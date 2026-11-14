import { useState } from "react";
import type { JSX } from "react";

/** A short interpretation task; feedback follows the learner's choice. */
export function EvidenceLesson(): JSX.Element {
  const [answer, setAnswer] = useState<string | null>(null);
  return (
    <section className="panel" aria-labelledby="lesson-heading">
      <h2 id="lesson-heading">Try the evidence lesson</h2>
      <p>
        A record has a positive estimated rate, but its valid test is not significant. What can you conclude?
      </p>
      <fieldset>
        <legend>Choose an interpretation before reading the guidance</legend>
        {(
          [
            ["no-change", "The environment has not changed."],
            [
              "evidence",
              "The estimated rate is positive, but evidence for a monotonic trend is insufficient.",
            ],
            ["cause", "The rate proves that one specific human activity caused the change."],
          ] as const
        ).map(([value, label]) => (
          <label className="lesson-choice" key={value}>
            <input
              type="radio"
              name="interpretation"
              value={value}
              checked={answer === value}
              onChange={() => setAnswer(value)}
            />{" "}
            {label}
          </label>
        ))}
      </fieldset>
      {answer !== null ? (
        <p role="status">
          {answer === "evidence" ? "Correct. " : "Review the distinction. "}
          An estimated rate, statistical evidence and causation answer different questions. A non-significant
          test does not prove no change; unavailable significance means no justified test was run. Compare
          places on identical complete years and check the NASA source and assumptions.
        </p>
      ) : null}
    </section>
  );
}
