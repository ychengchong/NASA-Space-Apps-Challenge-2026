/**
 * Picking a point on the globe by keyboard (spec 3: all controls work by keyboard). MapLibre
 * turns a focused globe with the arrow keys and zooms it with + and -; Enter then picks the point
 * at its centre, which a crosshair marks while the globe has focus.
 */

const PICK_KEY = "Enter";

/**
 * True when a key press should pick the globe's centre: Enter on the globe itself. Enter on a
 * control beside it, such as a zoom button, belongs to that control.
 */
export function picksMapCentre(
  event: { key: string; target: EventTarget | null },
  container: EventTarget,
): boolean {
  return event.key === PICK_KEY && event.target === container;
}
