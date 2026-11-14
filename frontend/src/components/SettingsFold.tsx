import { useId, useState } from "react";
import type { JSX, ReactNode } from "react";

interface SettingsFoldProps {
  /** What the button offers, such as "Change this case". */
  label: string;
  /** The settings behind it, in a few words. */
  hint: string;
  /**
   * True while the user has something to do in the settings, such as settings to check or a
   * picked point to place. The settings then stay open, and the button is left out.
   */
  needed: boolean;
  children: ReactNode;
}

/**
 * Settings that are folded away under an answer (spec 3): once a case or a map is on screen, its
 * settings wait behind one button, so the evidence follows the answer closely. The settings stay
 * in the page while folded, so what the user typed there is kept.
 */
export function SettingsFold({ label, hint, needed, children }: SettingsFoldProps): JSX.Element {
  const [opened, setOpened] = useState(false);
  const contentId = useId();
  const open = needed || opened;
  return (
    <div className="fold">
      {needed ? null : (
        <button
          type="button"
          className="fold-toggle"
          aria-expanded={open}
          aria-controls={contentId}
          onClick={() => setOpened(!open)}
        >
          <span className="fold-label">{label}</span>
          <span className="summary-hint">{hint}</span>
        </button>
      )}
      <div id={contentId} hidden={!open}>
        {children}
      </div>
    </div>
  );
}
