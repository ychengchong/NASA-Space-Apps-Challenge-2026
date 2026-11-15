/** The tabs of an open case's file, under the verdict, in order (spec 3, "Case file tabs"). */
export const CASE_TABS = [
  { id: "answer", label: "Answer" },
  { id: "explore", label: "Explore" },
  { id: "evidence", label: "Evidence" },
  { id: "learn", label: "Learn" },
] as const;

export type CaseTabId = (typeof CASE_TABS)[number]["id"];

/**
 * The tab a key moves to from tab `current` of `count`, by the ARIA tabs pattern: the arrow keys
 * step to the next or previous tab and wrap round, Home and End go to the first and last. Null
 * for any other key, which the tabs leave to the browser.
 */
export function tabAfterKey(key: string, current: number, count: number): number | null {
  switch (key) {
    case "ArrowRight":
      return (current + 1) % count;
    case "ArrowLeft":
      return (current - 1 + count) % count;
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return null;
  }
}
