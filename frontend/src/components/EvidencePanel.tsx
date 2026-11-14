import type { JSX } from "react";
import { seriesUrl } from "../api";
import type { Investigation, PlaceResult, Resolution, Trend, VariableSummary } from "../api";
import { cautionTexts } from "../cautions";
import { DATA_CAVEATS, POWER_ACKNOWLEDGEMENT, STATISTICS_LIMITS } from "../definitions";
import { formatCoordinates, formatNumber, formatPValue, formatSignedRate, withUnits } from "../format";
import { ShapeSwatch } from "./ShapeSwatch";
import { WordsUsedHere } from "./WordsUsedHere";

// The lag-1 autocorrelation and the correction factor are printed with two decimals, as in
// the steps the tool layer writes.
const MEMORY_DECIMALS = 2;

interface EvidencePanelProps {
  investigation: Investigation;
}

/** Every number behind the verdict, the cautions, the data source and the method (spec 3). */
export function EvidencePanel({ investigation }: EvidencePanelProps): JSX.Element {
  const { variable, results } = investigation;
  return (
    <section className="panel" aria-labelledby="evidence-heading">
      <details className="evidence">
        <summary>
          <h2 id="evidence-heading">Evidence</h2>
          <span className="summary-hint">The numbers, the method and the data behind the verdict</span>
        </summary>

        <h3>Numbers</h3>
        <NumbersTable results={results} variable={variable} />

        <h3>Cautions</h3>
        {results.map((result, index) => (
          <PlaceCautions
            key={index}
            result={result}
            index={index}
            variable={variable}
            showName={results.length > 1}
          />
        ))}

        <h3>Steps taken</h3>
        <ol className="steps">
          {investigation.steps.map((step, index) => (
            <li key={index}>{step}</li>
          ))}
        </ol>

        <h3>Data</h3>
        <ul className="plain-list">
          {investigation.sources.map((source, index) => (
            <li key={index}>
              {source.name}, version {source.version}, accessed {source.accessed}.
            </li>
          ))}
        </ul>
        <p>{POWER_ACKNOWLEDGEMENT}</p>
        <p>Download the values behind this case (CSV):</p>
        <ul className="download-list">
          {results.map((result, index) => (
            <li key={index}>
              {results.length > 1 ? <>{result.place.name}: </> : null}
              <a href={downloadUrl(investigation, result, "yearly")} download>
                yearly values
              </a>
              {", "}
              <a href={downloadUrl(investigation, result, "monthly")} download>
                monthly values
              </a>
            </li>
          ))}
        </ul>

        <WordsUsedHere variable={variable} />

        <h3>What the data can and cannot tell</h3>
        <ul className="plain-list">
          {[...DATA_CAVEATS, ...STATISTICS_LIMITS].map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function downloadUrl(investigation: Investigation, result: PlaceResult, resolution: Resolution): string {
  const { requested, variable } = investigation;
  return seriesUrl({
    variable: variable.id,
    place: { lat: result.place.lat, lon: result.place.lon },
    from: requested.from,
    to: requested.to,
    season: requested.season,
    resolution,
    format: "csv",
  });
}

interface Row {
  label: string;
  value: (result: PlaceResult) => string;
}

function numberRows(variable: VariableSummary): Row[] {
  const { decimals, rate_units: rateUnits } = variable;
  const perDecade = (rate: number): string =>
    `${withUnits(formatSignedRate(rate, decimals), rateUnits)} per decade`;
  const withTrend =
    (show: (trend: Trend) => string) =>
    (result: PlaceResult): string =>
      result.trend === null ? noTestText(result) : show(result.trend);
  return [
    { label: "Rate of change (Sen's slope)", value: withTrend((trend) => perDecade(trend.sen_slope)) },
    {
      label: "95% confidence interval of the rate",
      value: withTrend(
        (trend) =>
          `${formatSignedRate(trend.sen_ci95[0], decimals)} to ` +
          `${withUnits(formatSignedRate(trend.sen_ci95[1], decimals), rateUnits)} per decade`,
      ),
    },
    {
      label: "Total change over the years used",
      value: withTrend(
        (trend) =>
          `${withUnits(formatSignedRate(trend.total_change, decimals), rateUnits)} ` +
          `from ${trend.first_year} to ${trend.last_year}`,
      ),
    },
    {
      label: "Mann-Kendall p-value, after the correction",
      value: withTrend((trend) => formatPValue(trend.mk_p)),
    },
    {
      label: "Year-to-year memory (lag-1 autocorrelation, r1)",
      value: withTrend((trend) => formatNumber(trend.lag1, MEMORY_DECIMALS)),
    },
    {
      label: "Correction factor applied (f)",
      value: withTrend((trend) => formatNumber(trend.variance_factor, MEMORY_DECIMALS)),
    },
    { label: "Least-squares slope (cross-check)", value: withTrend((trend) => perDecade(trend.ols_slope)) },
    {
      label: "Least-squares p-value (t-test, same correction)",
      value: withTrend((trend) => formatPValue(trend.ols_p)),
    },
    { label: "Number of years used", value: withTrend((trend) => String(trend.n)) },
    {
      label: "First and last year used",
      value: withTrend((trend) => `${trend.first_year} to ${trend.last_year}`),
    },
    {
      label: "Grid cell",
      value: (result) => {
        const { cell } = result.place;
        return `centred on ${formatCoordinates(cell.lat, cell.lon)}, ${cell.height}° by ${cell.width}°`;
      },
    },
  ];
}

function noTestText(result: PlaceResult): string {
  return result.verdict.kind === "no_data" ? "No data" : "Not tested: too few years";
}

function NumbersTable({
  results,
  variable,
}: {
  results: PlaceResult[];
  variable: VariableSummary;
}): JSX.Element {
  const rows = numberRows(variable);
  return (
    <div className="table-scroll">
      <table className="data-table numbers-table">
        <caption className="visually-hidden">The statistics of each place</caption>
        <thead>
          <tr>
            <th scope="col">Measure</th>
            {results.map((result, index) => (
              <th scope="col" key={index}>
                <ShapeSwatch index={index} /> {result.place.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              {results.map((result, index) => (
                <td key={index}>{row.value(result)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlaceCautions({
  result,
  index,
  variable,
  showName,
}: {
  result: PlaceResult;
  index: number;
  variable: VariableSummary;
  showName: boolean;
}): JSX.Element {
  const texts = cautionTexts(result.verdict.cautions, variable, result.trend);
  return (
    <div className="place-cautions">
      {showName ? (
        <h4>
          <ShapeSwatch index={index} /> {result.place.name}
        </h4>
      ) : null}
      {texts.length === 0 ? (
        <p>No caution applies.</p>
      ) : (
        <ul className="caution-list">
          {texts.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
