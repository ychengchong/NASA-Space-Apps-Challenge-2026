import { useEffect, useState } from "react";
import type { JSX } from "react";

// Screen readers announce a live region's content only when it changes after the region is in
// the page, so the label waits this long after the empty region first appears.
const LIVE_REGION_DELAY_MS = 100;

/** The working state (spec 3): a progress line, announced to screen readers. */
export function ProgressLine({ active, label }: { active: boolean; label: string }): JSX.Element {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setReady(true), LIVE_REGION_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, []);
  return (
    <div className="progress" role="status">
      {active && ready ? (
        <>
          <span className="progress-bar" aria-hidden="true" />
          <span className="progress-label">{label}</span>
        </>
      ) : null}
    </div>
  );
}
