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

  test("gives no definition of 'significant' when the record was too short to test", () => {
    const verdict = { ...SIGNIFICANT_RISE, kind: "too_few_years" as const, direction: null };
    const html = renderToStaticMarkup(<VerdictCard investigation={investigation(verdict)} />);
    expect(html).not.toContain(SIGNIFICANCE_DEFINITION.definition);
  });
});
