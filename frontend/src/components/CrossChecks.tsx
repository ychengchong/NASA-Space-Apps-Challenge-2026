import { useId } from "react";
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
 * Other variables to test with the same places, period and season, as the last group of the
 * "Explore further" sheet (spec 3): the variable's related variables as cross-checks, and the
 * variables worth testing in the region type of a place, when that is known. Nothing when there
 * is neither.
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
    <section className="explore-variables" aria-labelledby="cross-checks-heading">
      <h3 id="cross-checks-heading">Test another variable</h3>
      <p className="explore-hint">
        Each link tests another variable with the same places, period and season.
      </p>
      {related.length > 0 ? (
        <VariableLinks
          label="Cross-check with a related variable"
          params={params}
          variables={related}
          onOpenPage={onOpenPage}
        />
      ) : null}
      {suggestions.map((suggestion) => (
        <VariableLinks
          key={suggestion.regionType}
          label={`Worth testing here (${joinWords(suggestion.placeNames)} · ${suggestion.regionType})`}
          params={params}
          variables={suggestion.variables}
          onOpenPage={onOpenPage}
        />
      ))}
    </section>
  );
}

/** One line of links to the same case with another variable, under the words that say why. */
function VariableLinks({
  label,
  params,
  variables,
  onOpenPage,
}: {
  label: string;
  params: CaseParams;
  variables: readonly VariableSummary[];
  onOpenPage: (url: string) => void;
}): JSX.Element {
  const labelId = useId();
  return (
    <div className="explore-links">
      <p id={labelId} className="explore-links-label">
        {label}
      </p>
      <ul aria-labelledby={labelId}>
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
    </div>
  );
}
