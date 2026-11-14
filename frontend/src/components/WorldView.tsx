import { useEffect, useMemo } from "react";
import type { JSX } from "react";
import { getWorld } from "../api";
import type { Investigation, WorldTrend } from "../api";
import { buildWorldQuery } from "../caseUrl";
import type { CasePlace, WorldParams } from "../caseUrl";
import { useGlobePlaces } from "../globeContext";
import type { MapPlace } from "../mapCell";
import { useRequest } from "../useRequest";
import { CaseLayout } from "./CaseLayout";
import { FileTab } from "./FileTab";
import { ProgressLine } from "./ProgressLine";
import { TrendChart } from "./TrendChart";
import { PlaceVerdict } from "./VerdictCard";

const APP_NAME = "Trend Detective";
const NO_PLACES: readonly MapPlace[] = [];

interface WorldViewProps {
  params: WorldParams;
  pickedPoint: CasePlace | null;
  onPick: (point: CasePlace) => void;
}

/**
 * A variable's trend in the frozen whole-world sample (spec 7, "The whole world"): its verdict,
 * which names the sample, the note on what a sample can describe, the chart and the evidence.
 * Every number and sentence is the API's.
 */
export function WorldView({ params, pickedPoint, onPick }: WorldViewProps): JSX.Element {
  const request = useRequest(`world:${buildWorldQuery(params)}`, (signal) => getWorld(params, signal));
  const { state } = request;
  const world = state.status === "done" ? state.value : state.status === "loading" ? state.stale : null;
  const chartInvestigation = useMemo(() => (world === null ? null : asInvestigation(world)), [world]);
  useGlobePlaces(NO_PLACES, pickedPoint, onPick);

  useEffect(() => {
    document.title = world === null ? APP_NAME : `${world.variable.name} in the whole world · ${APP_NAME}`;
    return () => {
      document.title = APP_NAME;
    };
  }, [world]);

  return (
    <CaseLayout
      answer={
        <>
          <ProgressLine active={state.status === "loading"} label="Reading the world sample…" />
          {state.status === "failed" ? (
            <p className="notice notice-error" role="alert">
              The whole world could not be shown. {state.error.message}
            </p>
          ) : null}
          <div className="live-region" aria-live="polite">
            {world !== null ? <WorldAnswer world={world} /> : null}
          </div>
          {chartInvestigation !== null ? (
            <TrendChart investigation={chartInvestigation} monthly={false} />
          ) : null}
        </>
      }
      side={null}
      main={world !== null ? <WorldEvidence world={world} /> : null}
    />
  );
}

export function WorldAnswer({ world }: { world: WorldTrend }): JSX.Element {
  return (
    <section className="panel verdict-card" aria-labelledby="verdict-heading">
      <FileTab label="Case file" />
      <h2 id="verdict-heading">The whole world</h2>
      <PlaceVerdict result={world.result} index={0} variable={world.variable} showName={false} />
      <p className="verdict-note">{world.sample_note}</p>
    </section>
  );
}

function WorldEvidence({ world }: { world: WorldTrend }): JSX.Element {
  return (
    <section className="panel" aria-labelledby="world-evidence-heading">
      <h2 id="world-evidence-heading">Evidence</h2>
      <h3>Steps taken</h3>
      <ol className="steps">
        {world.steps.map((step, index) => (
          <li key={index}>{step}</li>
        ))}
      </ol>
      <h3>Data</h3>
      <ul className="plain-list">
        {world.sources.map((source, index) => (
          <li key={index}>
            {source.name}, API {source.version}, accessed {source.accessed}. {source.product}.
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The world trend in the shape the chart reads; the chart shows no monthly values for it. */
function asInvestigation(world: WorldTrend): Investigation {
  return {
    id: world.app_url,
    variable: world.variable,
    requested: world.requested,
    results: [world.result],
    steps: world.steps,
    sources: world.sources,
    app_url: world.app_url,
  };
}
