import type { MouseEvent } from "react";

/**
 * Lets a plain click on a link open its page inside the app, without a page load. A click meant
 * for a new tab or window keeps the browser's own behaviour.
 */
export function followInApp(
  event: MouseEvent<HTMLAnchorElement>,
  url: string,
  open: (url: string) => void,
): void {
  const isPlainClick =
    event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  if (!isPlainClick) return;
  event.preventDefault();
  open(url);
}
