/**
 * Picking a point on the map by keyboard (spec 3: all controls work by keyboard). Leaflet moves a
 * focused map with the arrow keys and zooms it with + and -; Enter then picks the point at its
 * centre, which a crosshair marks while the map has focus.
 */

const PICK_KEY = "Enter";

/**
 * True when a key press should pick the map's centre: Enter on the map itself. Enter on a
 * control inside the map, such as a zoom button, belongs to that control.
 */
export function picksMapCentre(
  event: { key: string; target: EventTarget | null },
  container: EventTarget,
): boolean {
  return event.key === PICK_KEY && event.target === container;
}
