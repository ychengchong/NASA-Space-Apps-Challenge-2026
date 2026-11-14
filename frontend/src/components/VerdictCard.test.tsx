import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { SIGNIFICANCE_DEFINITION } from "../definitions";
import { investigation, SIGNIFICANT_RISE } from "./testData";
import { VerdictCard } from "./VerdictCard";

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
    expect(html).toContain("No upward or downward trend");
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
});
