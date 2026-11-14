import type { JSX } from "react";
import type { PlaceAction } from "../caseDraft";
import type { CasePlace } from "../caseUrl";
import { formatCoordinates } from "../format";
import { followInApp } from "../links";
import { PlaceActions } from "./PlaceSearch";

interface PickedPointProps {
  point: CasePlace;
  /** The places of the case as it stands, which decide what the point can become. */
  places: readonly CasePlace[];
  onChoose: (action: PlaceAction, place: CasePlace) => void;
  onDismiss: () => void;
  /** The point's overview: every variable's rate there (spec 7, "What is changing here?"). */
  overviewUrl: string;
  onOpenPage: (url: string) => void;
}

/**
 * The point the user picked on the globe, with what can be done with it (spec 3, "The globe").
 * It is shown on the stage, so the choice appears where the click was made. The stage is small
 * on a phone, so the buttons carry short labels and share one row.
 */
export function PickedPoint({
  point,
  places,
  onChoose,
  onDismiss,
  overviewUrl,
  onOpenPage,
}: PickedPointProps): JSX.Element {
  const coordinates = formatCoordinates(point.lat, point.lon);
  return (
    <div className="stage-card stage-pick" role="group" aria-label="The point you picked">
      <span className="candidate-name">You picked {coordinates}</span>
      <span className="stage-pick-buttons">
        <PlaceActions
          name={`The point you picked, ${coordinates}`}
          place={point}
          places={places}
          onChoose={onChoose}
          brief
        />
        <a
          className="button button-small button-secondary"
          href={overviewUrl}
          onClick={(event) => followInApp(event, overviewUrl, onOpenPage)}
        >
          What is changing here?
        </a>
        <button type="button" className="button button-small button-quiet" onClick={onDismiss}>
          Dismiss<span className="visually-hidden"> the picked point</span>
        </button>
      </span>
    </div>
  );
}
