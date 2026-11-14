import type { JSX } from "react";
import type { VariableSummary } from "../api";
import type { CaseParams } from "../caseUrl";
import { joinWords } from "../cautions";
import { regionTypeSuggestions, relatedVariables, withVariable } from "../crossChecks";
import { followInApp } from "../links";
import { regionTypeOf } from "../regionTypes";
import type { RegionTypes } from "../regionTypes";
import { casePageUrl } from "../route";

interface CrossChecksProps {
  /** The case on screen. */
  params: CaseParams;
  /** The catalogue, from /api/variables. */
  variables: readonly VariableSummary[];
  /** The region types known for places. */
  regionTypes: RegionTypes;
  onOpenPage: (url: string) => void;
}

/**
 * Other variables to test with the same places, period and season (spec 3, "The investigation
 * flow", step 6): the variable's related variables as cross-checks, and the variables worth
 * testing in the region type of a place, when that is known. Nothing when there is neither.
 */
export function CrossChecks({
  params,
  variables,
  regionTypes,
  onOpenPage,
}: CrossChecksProps): JSX.Element | null {
  const variable = variables.find((entry) => entry.id === params.variable);
  if (variable === undefined) return null;
  const related = relatedVariables(variable, variables);
  const suggestions = regionTypeSuggestions(
    params.places,
    (place) => regionTypeOf(regionTypes, place),
    variables,
    variable,
  );
  if (related.length === 0 && suggestions.length === 0) return null;

  return (
    <section className="panel" aria-labelledby="cross-checks-heading">
      <h2 id="cross-checks-heading">Dig deeper</h2>
      <p className="panel-note">Each link tests another variable with the same places, period and season.</p>
      {related.length > 0 ? (
        <>
          <h3>Cross-check with a related variable</h3>
          <VariableLinks params={params} variables={related} onOpenPage={onOpenPage} />
        </>
      ) : null}
      {suggestions.length > 0 ? (
        <>
          <h3>Worth testing here</h3>
          {suggestions.map((suggestion) => (
            <div key={suggestion.regionType}>
              <p className="field-hint">
                {joinWords(suggestion.placeNames)} · {suggestion.regionType}
              </p>
              <VariableLinks params={params} variables={suggestion.variables} onOpenPage={onOpenPage} />
            </div>
          ))}
        </>
      ) : null}
    </section>
  );
}

function VariableLinks({
  params,
  variables,
  onOpenPage,
}: {
  params: CaseParams;
  variables: readonly VariableSummary[];
  onOpenPage: (url: string) => void;
}): JSX.Element {
  return (
    <ul className="plain-list">
      {variables.map((variable) => {
        const url = casePageUrl(withVariable(params, variable.id));
        return (
          <li key={variable.id}>
            <a href={url} onClick={(event) => followInApp(event, url, onOpenPage)}>
              {variable.name}
            </a>
          </li>
        );
      })}
    </ul>
  );
}
