import type { JSX } from "react";
import type { ApiError, ExampleCase } from "../api";
import type { RequestState } from "../useRequest";
import { ExampleCases } from "./ExampleCases";

interface CaseProblemProps {
  error: ApiError;
  onRetry: () => void;
  examples: RequestState<ExampleCase[]>;
  onOpenExample: (url: string) => void;
}

/** Why a case could not run, in plain words, with the next step (spec 3 and spec 10). */
export function CaseProblem({ error, onRetry, examples, onOpenExample }: CaseProblemProps): JSX.Element {
  if (error.code === "source_unavailable") {
    return (
      <div className="notice notice-warning" role="alert">
        <h2>NASA&apos;s data service is not answering</h2>
        <p>{error.message}</p>
        <p>
          The data for this case is not saved here yet, so it cannot open right now. Try again in a minute.
          The example cases are saved, so they still open.
        </p>
        <p>
          <button type="button" className="button button-primary" onClick={onRetry}>
            Try again
          </button>
        </p>
        <ExampleCases examples={examples} onOpen={onOpenExample} />
      </div>
    );
  }
  if (isTemporary(error)) {
    return (
      <div className="notice notice-warning" role="alert">
        <h2>The case could not load</h2>
        <p>{error.message}</p>
        <p>
          <button type="button" className="button button-primary" onClick={onRetry}>
            Try again
          </button>
        </p>
      </div>
    );
  }
  return (
    <div className="notice notice-error" role="alert">
      <h2>This case cannot run</h2>
      <p>{error.message}</p>
      <p>Change the case settings to try again.</p>
    </div>
  );
}

function isTemporary(error: ApiError): boolean {
  return (
    error.code === "rate_limited" ||
    error.code === "network_error" ||
    error.code === "bad_response" ||
    error.code === "internal_error"
  );
}
