import type { JSX, ReactNode } from "react";

interface CaseLayoutProps {
  /** The verdict, on a case its chart, and the AI's notes, first on the page. */
  answer: ReactNode;
  /** The settings, under the answer. */
  side: ReactNode;
  /** The rest of the evidence, such as the key to the globe and the evidence panel, under the settings. */
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
