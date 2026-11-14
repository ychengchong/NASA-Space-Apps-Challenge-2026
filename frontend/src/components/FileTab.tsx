import type { JSX } from "react";

/**
 * The typed tab on the first sheet of the case file, the verdict (spec 3). It is the first thing
 * in its sheet, so it is read before the sheet's heading.
 */
export function FileTab({ label }: { label: string }): JSX.Element {
  return <p className="file-tab">{label}</p>;
}
