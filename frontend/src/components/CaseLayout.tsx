import type { JSX, ReactNode } from "react";

interface CaseLayoutProps {
  /** The verdict line, held at the top of the screen while the case scrolls (spec 3). */
  pinned?: ReactNode;
  /** The verdict, on a case its chart, and the AI's notes, first on the page. */
  answer: ReactNode;
  /** The settings, under the answer. */
  side?: ReactNode;
  /**
   * The rest of the evidence under the settings, such as a map's evidence. An open case has none:
   * its evidence is in the tabs of its answer.
   */
  main?: ReactNode;
}

/**
 * The page of an open case or map. The page holds the parts in the order they appear on screen
 * at every width, answer first, so Tab and screen readers meet the verdict first.
 */
export function CaseLayout({ pinned, answer, side, main }: CaseLayoutProps): JSX.Element {
  return (
    // A plain block round the column, so the verdict line's anchor takes no row or gap of the grid
    // and stays pinned for the whole case.
    <div className="case-file">
      {pinned}
      <div className="case-layout case-layout-open">
        <div className="case-answer">{answer}</div>
        {side !== undefined ? <div className="case-side">{side}</div> : null}
        {main !== undefined ? <div className="case-main">{main}</div> : null}
      </div>
    </div>
  );
}
