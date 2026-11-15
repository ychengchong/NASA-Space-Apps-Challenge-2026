import { useRef, useState } from "react";
import type { JSX, KeyboardEvent, ReactNode } from "react";
import { CASE_TABS, tabAfterKey } from "../caseTabs";
import type { CaseTabId } from "../caseTabs";

interface CaseTabsProps {
  /** What each tab holds. */
  panels: Readonly<Record<CaseTabId, ReactNode>>;
  /** Shown beside the row of tabs, such as "Change this case", whichever tab is chosen. */
  beside?: ReactNode;
}

/**
 * The case file under the verdict, in four tabs (spec 3, "Case file tabs"), by the ARIA tabs
 * pattern: one Tab stop for the row of tabs, the arrow keys to move along it. Every panel stays
 * in the page while hidden, so what was opened or typed in it is kept. The tab chosen is not part
 * of the address: a link reproduces the case, not the view.
 */
export function CaseTabs({ panels, beside }: CaseTabsProps): JSX.Element {
  const [selected, setSelected] = useState(0);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    const next = tabAfterKey(event.key, selected, CASE_TABS.length);
    if (next === null) return;
    event.preventDefault();
    setSelected(next);
    tabRefs.current[next]?.focus();
  };
  return (
    <div className="case-tabs">
      <div className="case-tab-row">
        <div className="case-tab-list" role="tablist" aria-label="Case file" onKeyDown={onKeyDown}>
          {CASE_TABS.map((tab, index) => (
            <button
              key={tab.id}
              ref={(element) => {
                tabRefs.current[index] = element;
              }}
              type="button"
              role="tab"
              id={`case-tab-${tab.id}`}
              className="case-tab"
              aria-selected={index === selected}
              aria-controls={`case-panel-${tab.id}`}
              tabIndex={index === selected ? 0 : -1}
              onClick={() => setSelected(index)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {beside}
      </div>
      {CASE_TABS.map((tab, index) => (
        <div
          key={tab.id}
          className="case-tab-panel"
          role="tabpanel"
          id={`case-panel-${tab.id}`}
          aria-labelledby={`case-tab-${tab.id}`}
          hidden={index !== selected}
        >
          {panels[tab.id]}
        </div>
      ))}
    </div>
  );
}
