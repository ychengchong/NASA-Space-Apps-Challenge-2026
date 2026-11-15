import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { SIGNIFICANCE_DEFINITION } from "../definitions";
import type { Investigation } from "../api";
import { investigation, placeResult, RECORDS, SIGNIFICANT_RISE } from "./testData";
import { VerdictCard } from "./VerdictCard";

/** Athens and Helsinki, each with a significant rise, under one summary sentence. */
function comparison(): Investigation {
  const athens = placeResult(SIGNIFICANT_RISE);
  athens.place = { ...athens.place, name: "Athens", lat: 37.98, lon: 23.73 };
  return {
    ...investigation(SIGNIFICANT_RISE),
    results: [athens, placeResult(SIGNIFICANT_RISE)],
    summary: "Both places rose.",
  };
}

describe("VerdictCard", () => {
  test("defines 'significant' next to a significant verdict", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).toContain(SIGNIFICANCE_DEFINITION.definition);
  });

  test("defines 'significant' next to a verdict that is not significant", () => {
    const verdict = { ...SIGNIFICANT_RISE, kind: "not_significant" as const };
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(verdict)} />);
    expect(html).toContain(SIGNIFICANCE_DEFINITION.definition);
  });

  test("names the direction in words beside its arrow", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).toContain('<span class="stamp-direction"><span aria-hidden="true">↑</span> Rising</span>');
    const falling = { ...SIGNIFICANT_RISE, direction: "falling" as const };
    expect(renderToStaticMarkup(<VerdictCard investigation={investigation(falling)} />)).toContain(
      '<span aria-hidden="true">↓</span> Falling',
    );
  });

  test("stamps a significant trend in the ink of its direction, under the kind of verdict", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).toContain('class="stamp stamp-rising"');
    expect(html).toContain('<span class="stamp-kind">Significant</span>');
    const falling = { ...SIGNIFICANT_RISE, direction: "falling" as const };
    expect(renderToStaticMarkup(<VerdictCard investigation={investigation(falling)} />)).toContain(
      'class="stamp stamp-falling"',
    );
  });

  test("stamps a trend that is not significant in faded ink, whatever its direction", () => {
    const verdict = { ...SIGNIFICANT_RISE, kind: "not_significant" as const };
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(verdict)} />);
    expect(html).toContain('class="stamp stamp-faded"');
    expect(html).toContain("Rising");
    expect(html).toContain('<span class="stamp-kind">Not significant</span>');
  });

  test("stamps a test with no direction as level, in a line short enough for the stamp", () => {
    const verdict = { ...SIGNIFICANT_RISE, kind: "not_significant" as const, direction: null };
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(verdict)} />);
    expect(html).toContain('class="stamp stamp-faded stamp-level"');
    expect(html).toContain("Zero estimated slope");
  });

  test("stamps a verdict that has no direction with its kind alone", () => {
    const verdict = { ...SIGNIFICANT_RISE, kind: "too_few_years" as const, direction: null };
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(verdict)} />);
    expect(html).toContain('<p class="stamp stamp-faded"><span class="stamp-kind">Too few years</span></p>');
  });

  test("carries the tab of the case file before the heading, without the case's internal code", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).toContain('<p class="file-tab">Case file</p>');
    expect(html.indexOf("file-tab")).toBeLessThan(html.indexOf('id="verdict-heading"'));
    expect(html).not.toContain(investigation(SIGNIFICANT_RISE).id);
  });

  test("shows the rate of a significant trend as a key figure, with its sign and units", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).toContain(
      '<span class="verdict-figure-number"><span class="verdict-figure-sign">+</span>0.05</span>',
    );
    expect(html).toContain('<span class="verdict-figure-units">°C per decade</span>');
  });

  test("shows no key figure for a trend that is not significant", () => {
    const verdict = { ...SIGNIFICANT_RISE, kind: "not_significant" as const };
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(verdict)} />);
    expect(html).not.toContain("verdict-figure");
  });

  test("gives no definition of 'significant' when the record was too short to test", () => {
    const verdict = { ...SIGNIFICANT_RISE, kind: "too_few_years" as const, direction: null };
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(verdict)} />);
    expect(html).not.toContain(SIGNIFICANCE_DEFINITION.definition);
  });

  test("keeps record years off the verdict card, which they would crowd", () => {
    const base = investigation(SIGNIFICANT_RISE);
    const withRecords = { ...base, results: base.results.map((result) => ({ ...result, records: RECORDS })) };
    const html = renderToStaticMarkup(<VerdictCard investigation={withRecords} />);
    expect(html).not.toContain(RECORDS.sentences[0] ?? "");
  });

  test("shows no record facts for a result without records", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).not.toContain("record-facts");
  });

  test("shows each place of a comparison at a glance, under the summary and above the fold", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={comparison()} />);
    const glance = html.slice(html.indexOf('<ul class="verdict-glance">'), html.indexOf("<details"));
    expect(html.indexOf("Both places rose.")).toBeLessThan(html.indexOf('<ul class="verdict-glance">'));
    expect(glance).toContain("Athens");
    expect(glance).toContain("Helsinki");
    expect(glance.match(/shape-swatch/g)).toHaveLength(2);
    expect(glance.match(/Rising · Significant/g)).toHaveLength(2);
  });

  test("keeps each place's full verdict and caution behind one closed fold in a comparison", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={comparison()} />);
    expect(html.match(/<details class="disclosure verdict-full">/g)).toHaveLength(1);
    const fold = html.indexOf('<details class="disclosure verdict-full">');
    expect(html.indexOf(SIGNIFICANT_RISE.sentence)).toBeGreaterThan(fold);
    expect(html.indexOf('class="stamp ')).toBeGreaterThan(fold);
  });

  test("shows the verdict of a single place in full, with no fold around it", () => {
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(SIGNIFICANT_RISE)} />);
    expect(html).not.toContain("verdict-full");
    expect(html).not.toContain("verdict-glance");
    expect(html).toContain(SIGNIFICANT_RISE.sentence);
  });
});
