import type { JSX } from "react";
import type { Investigation } from "../api";
import { formatCoordinates } from "../format";
import { periodText } from "../seasons";
import { ShapeSwatch } from "./ShapeSwatch";

/**
 * The caption of the globe on a wide screen (spec 3, "The globe"): the variable, each place
 * beside its marker's shape, and the period, so the globe explains itself, in a screenshot too.
 * A single place also gets its coordinates. Hidden from screen readers, because the case file
 * says the same.
 */
export function StageCaption({ investigation }: { investigation: Investigation }): JSX.Element {
  const { variable, requested, results } = investigation;
  const [first] = results;
  const period = periodText(requested);
  const detail =
    results.length === 1 && first !== undefined
      ? `${formatCoordinates(first.place.lat, first.place.lon)} · ${period}`
      : period;
  return (
    <div className="stage-card stage-caption" aria-hidden="true">
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
  );
}
