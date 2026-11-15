import { useContext } from "react";
import type { JSX, ReactNode } from "react";
import { createPortal } from "react-dom";
import { CaseRailContext } from "../caseRailContext";

/**
 * Draws its children in the results page's right-hand column, above the globe's panel (spec 3,
 * "Ask panel"). Where the page has no such column yet, as before it is in the page or when the
 * page is rendered without a document, the children stay where they are written.
 */
export function CaseRail({ children }: { children: ReactNode }): JSX.Element {
  const slot = useContext(CaseRailContext);
  return slot === null ? <>{children}</> : createPortal(children, slot);
}
