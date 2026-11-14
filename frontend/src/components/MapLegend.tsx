import type { JSX } from "react";
import type { TrendMap, VariableSummary } from "../api";
import { scaleEndDecimals, scaleGradient } from "../colourScale";
import { STRICTER_TEST_NOTE } from "../definitions";
import { formatSignedRate } from "../format";
import { periodText } from "../seasons";

/** The colour scale of the cells: what it measures, its two ends and which way is rising. */
function LegendScale({ variable, limit }: { variable: VariableSummary; limit: number }): JSX.Element {
  const unitsText = variable.rate_units === "" ? "per decade" : `${variable.rate_units} per decade`;
  const endDecimals = scaleEndDecimals(limit, variable.decimals);
  return (
    <>
      <p className="legend-title">Rate of change, {unitsText}</p>
      <div className="legend-scale">
        <span className="legend-gradient" style={{ background: scaleGradient() }} aria-hidden="true" />
        {limit > 0 ? (
          <span className="legend-ticks">
            <span>{formatSignedRate(-limit, endDecimals)}</span>
            <span>0</span>
            <span>{formatSignedRate(limit, endDecimals)}</span>
          </span>
        ) : null}
        <span className="legend-ends">
          <span>
            <span aria-hidden="true">←</span> Falling
          </span>
          <span>
            Rising <span aria-hidden="true">→</span>
          </span>
        </span>
      </div>
    </>
  );
}

/**
 * The key to the cells on the globe itself, on a wide screen (spec 3, "The globe"): the scale,
 * and beside it the two marks in a few words and the period. It is wide and low, because the
 * map keeps clear of it. Hidden from screen readers, because the "Trend in each grid cell" panel
 * holds the full legend.
 */
export function StageLegend({ trendMap, limit }: { trendMap: TrendMap; limit: number }): JSX.Element {
  return (
    <div className="stage-card stage-legend" aria-hidden="true">
      <div className="map-legend">
        <p className="stage-kicker">{trendMap.variable.name}</p>
        <LegendScale variable={trendMap.variable} limit={limit} />
      </div>
      <div className="map-legend">
        <ul className="legend-keys">
          <li>
            <span className="legend-swatch legend-mark" /> Passes the stricter test
          </li>
          <li>
            <span className="legend-swatch legend-hatch" /> No result
          </li>
        </ul>
        <p className="stage-detail">{periodText(trendMap.requested)}</p>
      </div>
    </div>
  );
}

/** The full legend of a region map, in its panel (spec 7, "Region view"). */
export function MapLegend({ variable, limit }: { variable: VariableSummary; limit: number }): JSX.Element {
  return (
    <div className="map-legend">
      <LegendScale variable={variable} limit={limit} />
      <ul className="legend-keys">
        <li>
          <span className="legend-swatch legend-mark" aria-hidden="true" /> Dot: the cell passes the
          map&apos;s stricter test
        </li>
        <li>
          <span className="legend-swatch legend-hatch" aria-hidden="true" /> Hatched: no result, because the
          cell has too few complete years to test
        </li>
      </ul>
      <p className="legend-note">{STRICTER_TEST_NOTE}</p>
    </div>
  );
}
