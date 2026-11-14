import type { JSX } from "react";
import { formatCoordinates } from "../format";
import { useGlobe } from "../globeContext";
import type { MapPlace } from "../mapCell";
import type { LatLon } from "../regionBox";
import { ShapeSwatch } from "./ShapeSwatch";

// Spec 3, "Wording and accessibility": the globe's note reads exactly this.
const PICK_NOTE =
  "Click the globe to pick a point, or search for a place in the case settings. With a keyboard, " +
  "focus the globe, turn it with the arrow keys and press Enter to pick the point at its centre.";
const UNAVAILABLE_NOTE =
  "The globe could not start in this browser, so search for a place in the case settings instead.";

interface PlaceLegendProps {
  places: readonly MapPlace[];
  /** The point picked on the globe that is not yet a place of the case. */
  pickedPoint: LatLon | null;
}

/**
 * The key to the globe (spec 3): each place with its marker and the grid cell its values
 * describe, and how to pick a point. The list names every place, so nothing on the globe is
 * told by colour or position alone.
 */
export function PlaceLegend({ places, pickedPoint }: PlaceLegendProps): JSX.Element {
  const { handle, status } = useGlobe();
  const hasCells = places.some((place) => place.cell !== undefined);
  return (
    <section className="panel" aria-labelledby="globe-heading">
      <h2 id="globe-heading">On the globe</h2>
      {places.length > 0 ? (
        <ul className="map-places">
          {places.map((place, index) => (
            <li key={index}>
              <ShapeSwatch index={index} /> {placeCaption(place)}
            </li>
          ))}
        </ul>
      ) : null}
      <p className="panel-note">{status === "unavailable" ? UNAVAILABLE_NOTE : PICK_NOTE}</p>
      {hasCells ? (
        <p className="globe-actions">
          <button
            type="button"
            className="button button-secondary"
            disabled={handle === null}
            onClick={() => handle?.zoomToCells()}
          >
            {places.length > 1 ? "Zoom in to the grid cells" : "Zoom in to the grid cell"}
          </button>
        </p>
      ) : null}
      <p className="status-text" role="status">
        {pickedPoint === null
          ? ""
          : `You picked ${formatCoordinates(pickedPoint.lat, pickedPoint.lon)}. Choose what to do with it on the globe.`}
      </p>
    </section>
  );
}

function placeCaption(place: MapPlace): string {
  const { cell } = place;
  if (cell === undefined) return `${place.name}: ${formatCoordinates(place.lat, place.lon)}`;
  return (
    `${place.name}: grid cell centred on ${formatCoordinates(cell.lat, cell.lon)}, ` +
    `${cell.height}° by ${cell.width}°. The outline shows the cell the values describe.`
  );
}
