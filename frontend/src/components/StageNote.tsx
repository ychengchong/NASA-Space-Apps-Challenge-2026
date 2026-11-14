import { useContext } from "react";
import type { JSX, ReactNode } from "react";
import { createPortal } from "react-dom";
import { StageNoteContext } from "../globeContext";

/**
 * Draws its children on the globe's stage, in its lower left corner (spec 3, "The globe"). The
 * view that knows what the globe shows lies in the case file, outside the stage, so its note is
 * drawn into the element the stage keeps for it. Nothing is drawn before the stage is in the
 * page, or where there is no globe.
 */
export function StageNote({ children }: { children: ReactNode }): JSX.Element | null {
  const slot = useContext(StageNoteContext);
  return slot === null ? null : createPortal(children, slot);
}
