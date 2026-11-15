import { useEffect, useState } from "react";
import type { RefObject } from "react";

/**
 * True when an element is out of view because the page has scrolled past it, so its whole box
 * lies above the top of the screen; false while any of it shows, or when it lies below.
 */
export function isScrolledPast(isIntersecting: boolean, bottomPx: number): boolean {
  return !isIntersecting && bottomPx <= 0;
}

/**
 * Whether the page has scrolled past the element `ref` points at (`isScrolledPast`), watched with
 * an IntersectionObserver so nothing runs on each scroll event. False where the browser has none.
 */
export function useScrolledPast(ref: RefObject<HTMLElement | null>): boolean {
  const [past, setPast] = useState(false);
  useEffect(() => {
    const element = ref.current;
    if (element === null || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry !== undefined) setPast(isScrolledPast(entry.isIntersecting, entry.boundingClientRect.bottom));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  return past;
}
