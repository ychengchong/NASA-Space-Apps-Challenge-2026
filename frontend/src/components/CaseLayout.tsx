import type { JSX, ReactNode } from "react";

interface CaseLayoutProps {
  /** The verdict and the AI's notes: across the top on a wide screen. */
  answer: ReactNode;
  /** The settings: the left column under the answer on a wide screen. */
  side: ReactNode;
  /** The chart, the map and the evidence: the right column under the answer on a wide screen. */
  main: ReactNode;
}

/**
 * The page of an open case or map. The page holds the parts in the order they appear on screen
 * at every width, answer first, so Tab and screen readers meet the verdict first.
 */
export function CaseLayout({ answer, side, main }: CaseLayoutProps): JSX.Element {
  return (
    <div className="case-layout case-layout-open">
      <div className="case-answer">{answer}</div>
      <div className="case-side">{side}</div>
      <div className="case-main">{main}</div>
    </div>
  );
}
