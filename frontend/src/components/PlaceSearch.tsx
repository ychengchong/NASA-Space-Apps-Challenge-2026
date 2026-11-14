import { useEffect, useState } from "react";
import type { JSX, Ref } from "react";
import { getPlaces } from "../api";
import type { PlaceCandidate } from "../api";
import { placeActions, placeFromCandidate, placeName } from "../caseDraft";
import type { PlaceAction } from "../caseDraft";
import { MAX_PLACES } from "../caseUrl";
import type { CasePlace } from "../caseUrl";
import { useRequest } from "../useRequest";
import type { RequestState } from "../useRequest";

// The place search waits for a pause in typing, so it does not ask on every key.
const SEARCH_DELAY_MS = 300;
const MIN_SEARCH_LENGTH = 2;

function actionLabel(action: PlaceAction, places: readonly CasePlace[]): string {
  const current = places[0] === undefined ? "" : placeName(places[0]);
  switch (action) {
    case "use":
      return "Use this place";
    case "replace":
      return `Use instead of ${current}`;
    case "compare":
      return `Compare with ${current}`;
    case "add":
      return "Add to the comparison";
  }
}

/** The buttons that put a place into the case, or why it cannot go in. */
export function PlaceActions({
  name,
  place,
  places,
  onChoose,
}: {
  name: string;
  place: CasePlace;
  places: readonly CasePlace[];
  onChoose: (action: PlaceAction, place: CasePlace) => void;
}): JSX.Element {
  const actions = placeActions(places, place);
  if (actions.length === 0) {
    const reason =
      places.length >= MAX_PLACES
        ? `A case holds at most ${MAX_PLACES} places. Remove one to add another.`
        : "Already in this case.";
    return <span className="candidate-detail">{reason}</span>;
  }
  return (
    <span className="candidate-actions">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          className="button button-small"
          onClick={() => onChoose(action, place)}
        >
          <span className="visually-hidden">{name}: </span>
          {actionLabel(action, places)}
        </button>
      ))}
    </span>
  );
}

function candidateDetail(candidate: PlaceCandidate): string {
  const kind = candidate.region_type ?? candidate.kind;
  return candidate.country ? `${candidate.country} · ${kind}` : kind;
}

/** Finds places by name in the place list (spec 6), each with the buttons that put it into the case. */
export function PlaceSearch({
  places,
  onChoose,
  inputRef,
}: {
  places: readonly CasePlace[];
  onChoose: (action: PlaceAction, place: CasePlace, candidate: PlaceCandidate) => void;
  inputRef: Ref<HTMLInputElement>;
}): JSX.Element {
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(text.trim()), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [text]);
  const search = useRequest(query.length >= MIN_SEARCH_LENGTH ? query : null, (signal) =>
    getPlaces(query, signal),
  );
  const results = search.state.status === "done" ? search.state.value : [];

  const choose = (action: PlaceAction, place: CasePlace, candidate: PlaceCandidate): void => {
    onChoose(action, place, candidate);
    setText("");
    setQuery("");
  };

  return (
    <div className="place-search">
      <label htmlFor="place-search" className="field-sublabel">
        {places.length === 0 ? "Find a place" : "Find another place"}
      </label>
      <input
        id="place-search"
        ref={inputRef}
        type="search"
        value={text}
        placeholder="A city or a region, such as Helsinki"
        autoComplete="off"
        onChange={(event) => setText(event.target.value)}
      />
      <p className="status-text" role="status">
        {searchStatus(search.state, query)}
      </p>
      {results.length > 0 ? (
        <ul className="candidate-list">
          {results.map((candidate) => {
            const place = placeFromCandidate(candidate);
            return (
              <li key={`${candidate.name},${candidate.lat},${candidate.lon}`} className="candidate">
                <span className="candidate-name">{candidate.name}</span>
                <span className="candidate-detail">{candidateDetail(candidate)}</span>
                <PlaceActions
                  name={candidate.name}
                  place={place}
                  places={places}
                  onChoose={(action) => choose(action, place, candidate)}
                />
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

function searchStatus(state: RequestState<PlaceCandidate[]>, query: string): string {
  if (state.status === "loading") return "Searching…";
  if (state.status === "failed") return `The search failed. ${state.error.message}`;
  if (state.status === "done" && state.value.length === 0) return `No place matches “${query}”.`;
  if (state.status === "done")
    return state.value.length === 1 ? "1 place found." : `${state.value.length} places found.`;
  return "";
}
