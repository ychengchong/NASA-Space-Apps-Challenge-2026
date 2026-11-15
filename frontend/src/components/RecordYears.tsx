import type { JSX } from "react";
import type { PlaceResult, VariableSummary } from "../api";
import { recordRows } from "../recordRows";
import type { RecordRow } from "../recordRows";
import { ShapeSwatch } from "./ShapeSwatch";

interface RecordYearsProps {
  results: readonly PlaceResult[];
  variable: VariableSummary;
  /** True when the places are named, as in a comparison. */
  showNames?: boolean;
}

/**
 * The record years of each place (spec 7, "Record years") on a sheet of their own, after the
 * chart that rings them: a small table of the API's fields, then the API's note, once, that they
 * are not tests. Nothing shows when no place has records.
 */
export function RecordYears({ results, variable, showNames = false }: RecordYearsProps): JSX.Element | null {
  const withRecords = results.flatMap((result, index) =>
    result.records === null || result.records === undefined
      ? []
      : [{ result, records: result.records, index }],
  );
  const note = withRecords[0]?.records.note;
  if (note === undefined) return null;
  const units = variable.units === "" ? "" : ` (${variable.units})`;
  return (
    <section className="panel sheet record-years" aria-labelledby="records-heading">
      {/* The units sit beside the heading, so one place's table needs no caption line. */}
      <div className="panel-heading-row">
        <h2 id="records-heading">Record years</h2>
        <p id="records-units" className="record-units">
          yearly values used{units}
        </p>
      </div>
      {withRecords.map(({ result, records, index }) => (
        <table
          key={index}
          className="record-table"
          aria-labelledby={showNames ? undefined : "records-heading records-units"}
        >
          {showNames ? (
            <caption>
              <ShapeSwatch index={index} /> {result.place.name}
            </caption>
          ) : null}
          <tbody>
            {recordRows(records, variable).map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                <td>
                  <RowCells row={row} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ))}
      <p className="panel-note">{note}</p>
    </section>
  );
}

function RowCells({ row }: { row: RecordRow }): JSX.Element {
  switch (row.kind) {
    case "sentence":
      return <>{row.sentence}</>;
    case "years":
      return (
        <ul className="record-years-list">
          {row.items.map((item) => (
            <li key={item.year}>
              <span className="record-year">{item.year}</span> {item.value}
            </li>
          ))}
        </ul>
      );
    case "window":
      return (
        <>
          {row.last} · {row.first} · change <strong>{row.change}</strong>
        </>
      );
  }
}
