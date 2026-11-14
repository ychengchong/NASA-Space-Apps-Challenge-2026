import type { JSX } from "react";

/**
 * Stands in for the verdict while a case or a map loads for the first time (spec 3, "States the
 * screen must handle"), so the case file keeps its shape. Hidden from screen readers: the
 * progress line says what is happening.
 */
export function VerdictSkeleton(): JSX.Element {
  return (
    <div className="panel skeleton" aria-hidden="true">
      <span className="skeleton-line skeleton-label" />
      <span className="skeleton-line skeleton-figure" />
      <span className="skeleton-line" />
      <span className="skeleton-line skeleton-short" />
    </div>
  );
}

/** Stands in for the chart, as VerdictSkeleton does for the verdict. */
export function ChartSkeleton(): JSX.Element {
  return (
    <div className="panel skeleton" aria-hidden="true">
      <span className="skeleton-line skeleton-label" />
      <span className="skeleton-line skeleton-chart" />
    </div>
  );
}
