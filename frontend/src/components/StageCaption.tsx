import type { JSX } from "react";
import type { Investigation } from "../api";
import { formatCoordinates } from "../format";
import { useGlobe } from "../globeContext";
import { periodText } from "../seasons";
import { ShapeSwatch } from "./ShapeSwatch";

interface StageCaptionProps {
  investigation: Investigation;
  /** How many of the places have their grid cell drawn on the globe. */
  cellCount: number;
}

/**
 * The caption of the globe on a wide screen (spec 3, "The globe"): the variable, each place
 * beside its marker's shape, and the period, so the globe explains itself, in a screenshot too.
 * A single place also gets its coordinates. Its words are hidden from screen readers, because
 * the case file says the same. Once the places have grid cells on the globe, a button under the
 * words closes in on them.
 */
export function StageCaption({ investigation, cellCount }: StageCaptionProps): JSX.Element {
  const { handle } = useGlobe();
  const { variable, requested, results } = investigation;
  const [first] = results;
  const period = periodText(requested);
  const detail =
    results.length === 1 && first !== undefined
      ? `${formatCoordinates(first.place.lat, first.place.lon)} · ${period}`
      : period;
  return (
    <div className="stage-card stage-caption">
      <div aria-hidden="true">
        <p className="stage-kicker">{variable.name}</p>
        <ul className="stage-places">
          {results.map((result, index) => (
            <li key={index}>
              <ShapeSwatch index={index} /> {result.place.name}
            </li>
          ))}
        </ul>
        <p className="stage-detail">{detail}</p>
      </div>
      {cellCount > 0 ? (
        <button
          type="button"
          className="button button-small"
          disabled={handle === null}
          onClick={() => handle?.zoomToCells()}
        >
          {cellCount > 1 ? "Zoom in to the grid cells" : "Zoom in to the grid cell"}
        </button>
      ) : null}
    </div>
  );
}
