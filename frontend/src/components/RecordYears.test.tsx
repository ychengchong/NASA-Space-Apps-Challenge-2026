import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { RecordYears } from "./RecordYears";
import { AIR_TEMP, placeResult, RECORDS, SIGNIFICANT_RISE } from "./testData";

const WITH_RECORDS = { ...placeResult(SIGNIFICANT_RISE), records: RECORDS };

describe("RecordYears", () => {
  test("shows the record years as a small table of the API's fields, then the note once", () => {
    const html = renderToStaticMarkup(<RecordYears results={[WITH_RECORDS]} variable={AIR_TEMP} />);
    expect(html).toContain(">Record years</h2>");
    expect(html).toContain("yearly values used (°C)");
    expect(html).toContain('<span class="record-year">2020</span> 8.26');
    expect(html).toContain('<span class="record-year">1987</span> 2.88');
    expect(html).toContain("2016 to 2025: 7.20 · 1981 to 1990: 4.80 · change <strong>+2.40 °C</strong>");
    expect(html.split(RECORDS.note)).toHaveLength(2);
    expect(html).not.toContain(RECORDS.sentences[0] ?? "");
  });

  test("labels one place's table by the heading and its units, with no caption line", () => {
    const html = renderToStaticMarkup(<RecordYears results={[WITH_RECORDS]} variable={AIR_TEMP} />);
    expect(html).toContain('aria-labelledby="records-heading records-units"');
    expect(html).not.toContain("<caption>");
  });

  test("names each place in a comparison, with its marker, and gives the note once", () => {
    const athens = { ...WITH_RECORDS, place: { ...WITH_RECORDS.place, name: "Athens" } };
    const html = renderToStaticMarkup(
      <RecordYears results={[athens, WITH_RECORDS]} variable={AIR_TEMP} showNames />,
    );
    expect(html).toContain('aria-hidden="true"></span> Athens</caption>');
    expect(html).toContain('aria-hidden="true"></span> Helsinki</caption>');
    expect(html.split("<table").filter((part) => part.includes("shape-swatch"))).toHaveLength(2);
    expect(html.split(RECORDS.note)).toHaveLength(2);
  });

  test("shows nothing when no place has records", () => {
    expect(
      renderToStaticMarkup(<RecordYears results={[placeResult(SIGNIFICANT_RISE)]} variable={AIR_TEMP} />),
    ).toBe("");
  });
});
