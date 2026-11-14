import { useId, useRef, useState } from "react";
import type { JSX, KeyboardEvent, Ref } from "react";
import type { PlaceCandidate, VariableSummary } from "../api";
import { applyPlaceAction, caseFromDraft, parseYearText, placeName, removePlace } from "../caseDraft";
import type { CaseDraft, PlaceAction } from "../caseDraft";
import type { CasePlace } from "../caseUrl";
import { PERIOD_CAUTION } from "../definitions";
import { formatCoordinates } from "../format";
import { isSeason, SEASON_LABELS, SEASON_ORDER } from "../seasons";
import type { RequestState } from "../useRequest";
import { PlaceActions, PlaceSearch } from "./PlaceSearch";
import { ShapeSwatch } from "./ShapeSwatch";

interface CaseSettingsProps {
  draft: CaseDraft;
  variables: RequestState<VariableSummary[]>;
  /** True when edits wait for "Run this case"; false when each edit reloads the open case. */
  pending: boolean;
  /** A point picked on the map, offered like a search result. */
  pickedPoint: CasePlace | null;
  onDismissPickedPoint: () => void;
  /** Called with a place chosen from the place search, before the draft changes. */
  onPickCandidate: (candidate: PlaceCandidate) => void;
  onChange: (draft: CaseDraft) => void;
  onRun: () => void;
  /** Given while a case is open behind pending settings: drops the pending settings. */
  onCancel?: () => void;
  headingRef?: Ref<HTMLHeadingElement>;
}

/** Shows exactly what is tested, and lets the user change every part of it (spec 3). */
export function CaseSettings({
  draft,
  variables,
  pending,
  pickedPoint,
  onDismissPickedPoint,
  onPickCandidate,
  onChange,
  onRun,
  onCancel,
  headingRef,
}: CaseSettingsProps): JSX.Element {
  const recordStart = selectedVariable(variables, draft.variable)?.record_start ?? null;
  const searchRef = useRef<HTMLInputElement>(null);
  // Choosing or removing a place takes the pressed button out of the page, so focus moves to the
  // place search, which stays, instead of falling back to the document.
  const focusSearch = (): void => searchRef.current?.focus();
  const choosePlace = (action: PlaceAction, place: CasePlace): void => {
    onChange(applyPlaceAction(draft, action, place));
    focusSearch();
  };
  const removePlaceAt = (index: number): void => {
    onChange(removePlace(draft, index));
    focusSearch();
  };

  return (
    <section className="panel case-settings" aria-labelledby="settings-heading">
      <h2 id="settings-heading" ref={headingRef} tabIndex={-1}>
        Case settings
      </h2>
      <p className="panel-note">
        {pending ? "Check these settings, then run the case." : "Each change reloads the case."}
      </p>

      <VariableField draft={draft} variables={variables} onChange={onChange} />

      <fieldset className="field">
        <legend className="field-label">Places</legend>
        <PlaceList draft={draft} pending={pending} onRemove={removePlaceAt} />
        {pickedPoint !== null ? (
          <PickedPoint
            point={pickedPoint}
            places={draft.places}
            onChoose={(action, place) => {
              choosePlace(action, place);
              onDismissPickedPoint();
            }}
            onDismiss={() => {
              onDismissPickedPoint();
              focusSearch();
            }}
          />
        ) : null}
        <PlaceSearch
          places={draft.places}
          onChoose={(action, place, candidate) => {
            onPickCandidate(candidate);
            choosePlace(action, place);
          }}
          inputRef={searchRef}
        />
      </fieldset>

      <PeriodFields
        from={draft.from}
        to={draft.to}
        recordStart={recordStart}
        onCommit={(from, to) => onChange(withPeriod(draft, from, to))}
      />

      <div className="field">
        <label htmlFor="season" className="field-label">
          Season
        </label>
        <select
          id="season"
          value={draft.season}
          onChange={(event) => {
            const season = event.target.value;
            if (isSeason(season)) onChange({ ...draft, season });
          }}
        >
          {SEASON_ORDER.map((season) => (
            <option key={season} value={season}>
              {SEASON_LABELS[season]}
            </option>
          ))}
        </select>
      </div>

      {pending ? <RunRow draft={draft} onRun={onRun} onCancel={onCancel} /> : null}
    </section>
  );
}

function withPeriod(draft: CaseDraft, from: number | undefined, to: number | undefined): CaseDraft {
  const next: CaseDraft = { variable: draft.variable, places: draft.places, season: draft.season };
  if (from !== undefined) next.from = from;
  if (to !== undefined) next.to = to;
  return next;
}

function selectedVariable(
  variables: RequestState<VariableSummary[]>,
  id: string | null,
): VariableSummary | undefined {
  if (variables.status !== "done" || id === null) return undefined;
  return variables.value.find((variable) => variable.id === id);
}

function themeLabel(theme: string): string {
  return theme.charAt(0).toUpperCase() + theme.slice(1);
}

function VariableField({
  draft,
  variables,
  onChange,
}: {
  draft: CaseDraft;
  variables: RequestState<VariableSummary[]>;
  onChange: (draft: CaseDraft) => void;
}): JSX.Element {
  const [showDefinition, setShowDefinition] = useState(false);
  const definitionId = useId();
  const list = variables.status === "done" ? variables.value : [];
  const selected = selectedVariable(variables, draft.variable);
  const themes = [...new Set(list.map((variable) => variable.theme))];
  const isUnknown = draft.variable !== null && variables.status === "done" && selected === undefined;

  return (
    <div className="field">
      <label htmlFor="variable" className="field-label">
        Variable
      </label>
      <div className="field-inline">
        <select
          id="variable"
          value={draft.variable ?? ""}
          disabled={variables.status !== "done"}
          onChange={(event) => onChange({ ...draft, variable: event.target.value })}
        >
          {draft.variable === null ? <option value="">Choose a variable</option> : null}
          {isUnknown ? (
            <option value={draft.variable ?? ""}>Unknown variable: {draft.variable}</option>
          ) : null}
          {themes.map((theme) => (
            <optgroup key={theme} label={themeLabel(theme)}>
              {list
                .filter((variable) => variable.theme === theme)
                .map((variable) => (
                  <option key={variable.id} value={variable.id}>
                    {variable.name}
                  </option>
                ))}
            </optgroup>
          ))}
        </select>
        <button
          type="button"
          className="button button-secondary"
          aria-expanded={showDefinition}
          aria-controls={definitionId}
          disabled={selected === undefined}
          onClick={() => setShowDefinition((shown) => !shown)}
        >
          What is this?
        </button>
      </div>
      {variables.status === "loading" ? <p className="field-hint">Loading the variables…</p> : null}
      {variables.status === "failed" ? (
        <p className="field-error">The variables could not be loaded. {variables.error.message}</p>
      ) : null}
      <div id={definitionId} className="definition-box" hidden={!showDefinition || selected === undefined}>
        {selected !== undefined ? (
          <>
            <p>{selected.definition}</p>
            <p>
              Units: {selected.units}. The record starts in {selected.record_start}.
            </p>
            {selected.trend_note ? <p>Note: {selected.trend_note}</p> : null}
          </>
        ) : null}
      </div>
    </div>
  );
}

function PlaceList({
  draft,
  pending,
  onRemove,
}: {
  draft: CaseDraft;
  pending: boolean;
  onRemove: (index: number) => void;
}): JSX.Element {
  if (draft.places.length === 0) {
    return <p className="field-hint">No place yet. Search for one below, or click the map.</p>;
  }
  // An open case needs a place, so its last place can only be replaced, not removed.
  const canRemove = pending || draft.places.length > 1;
  return (
    <ul className="place-list">
      {draft.places.map((place, index) => (
        <li key={`${index}:${place.lat},${place.lon}`} className="place-row">
          <ShapeSwatch index={index} />
          <span className="place-name">{placeName(place)}</span>
          {canRemove ? (
            <button type="button" className="button button-small" onClick={() => onRemove(index)}>
              Remove<span className="visually-hidden"> {placeName(place)}</span>
            </button>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function PickedPoint({
  point,
  places,
  onChoose,
  onDismiss,
}: {
  point: CasePlace;
  places: readonly CasePlace[];
  onChoose: (action: PlaceAction, place: CasePlace) => void;
  onDismiss: () => void;
}): JSX.Element {
  const name = `The point you picked, ${formatCoordinates(point.lat, point.lon)}`;
  return (
    <div className="candidate picked-point">
      <span className="candidate-name">{name}</span>
      <PlaceActions name={name} place={point} places={places} onChoose={onChoose} />
      <button type="button" className="button button-small button-quiet" onClick={onDismiss}>
        Dismiss<span className="visually-hidden"> the picked point</span>
      </button>
    </div>
  );
}

function PeriodFields({
  from,
  to,
  recordStart,
  onCommit,
}: {
  from: number | undefined;
  to: number | undefined;
  recordStart: number | null;
  onCommit: (from: number | undefined, to: number | undefined) => void;
}): JSX.Element {
  const [fromText, setFromText] = useState(yearText(from));
  const [toText, setToText] = useState(yearText(to));
  const [error, setError] = useState<string | null>(null);
  // When the case's period changes, such as after the API clamps it, the boxes show the new years.
  // Adjusting state while rendering keeps focus in the box, where a remount would lose it.
  const [shown, setShown] = useState({ from, to });
  if (shown.from !== from || shown.to !== to) {
    setShown({ from, to });
    setFromText(yearText(from));
    setToText(yearText(to));
  }

  const commit = (): void => {
    const nextFrom = parseYearText(fromText);
    const nextTo = parseYearText(toText);
    if (nextFrom === "invalid" || nextTo === "invalid") {
      setError("Enter a year with four digits, such as 1990, or leave the box empty.");
      return;
    }
    if (nextFrom !== undefined && nextTo !== undefined && nextFrom > nextTo) {
      setError("The first year must not be later than the last year.");
      return;
    }
    setError(null);
    if (nextFrom !== from || nextTo !== to) onCommit(nextFrom, nextTo);
  };
  const commitOnEnter = (event: KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === "Enter") commit();
  };

  return (
    <fieldset className="field">
      <legend className="field-label">Period</legend>
      <div className="field-row">
        <label className="year-field">
          <span className="field-sublabel">From</span>
          <input
            type="text"
            inputMode="numeric"
            value={fromText}
            placeholder="First year"
            onChange={(event) => setFromText(event.target.value)}
            onBlur={commit}
            onKeyDown={commitOnEnter}
          />
        </label>
        <label className="year-field">
          <span className="field-sublabel">To</span>
          <input
            type="text"
            inputMode="numeric"
            value={toText}
            placeholder="Last year"
            onChange={(event) => setToText(event.target.value)}
            onBlur={commit}
            onKeyDown={commitOnEnter}
          />
        </label>
      </div>
      <p className="field-hint">
        Both years count. Leave a box empty to use the whole record
        {recordStart === null ? "" : `, which starts in ${recordStart}`}. Press Enter or leave the box to
        apply.
      </p>
      {error !== null ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
      <p className="caution">
        <strong>Caution:</strong> {PERIOD_CAUTION}
      </p>
    </fieldset>
  );
}

function yearText(year: number | undefined): string {
  return year === undefined ? "" : String(year);
}

function RunRow({
  draft,
  onRun,
  onCancel,
}: {
  draft: CaseDraft;
  onRun: () => void;
  onCancel: (() => void) | undefined;
}): JSX.Element {
  const ready = caseFromDraft(draft) !== null;
  return (
    <div className="run-row">
      <button type="button" className="button button-primary" disabled={!ready} onClick={onRun}>
        Run this case
      </button>
      {onCancel !== undefined ? (
        <button type="button" className="button button-secondary" onClick={onCancel}>
          Cancel
        </button>
      ) : null}
      {ready ? null : <p className="field-hint">Choose a variable and at least one place first.</p>}
    </div>
  );
}
