import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import type { ExampleCase } from "../api";
import { ExampleCases } from "./ExampleCases";

const EXAMPLES: ExampleCase[] = [
  {
    title: "Is Svalbard getting warmer?",
    teaser: "Air temperature in Longyearbyen.",
    query: "v=air_temp&p=78.22,15.65&label=Longyearbyen&from=1981&to=2025&s=annual",
  },
  {
    title: "Rain in Athens and Helsinki",
    teaser: "Two cities, one variable.",
    query:
      "v=precipitation&p=37.98,23.73&p=60.17,24.94&label=Athens&label=Helsinki&from=1981&to=2025&s=annual",
  },
];

function render(examples: ExampleCase[], onGlobe = false): string {
  return renderToStaticMarkup(
    <ExampleCases
      examples={{ status: "done", value: examples }}
      onOpen={() => undefined}
      onGlobe={onGlobe}
    />,
  );
}

describe("ExampleCases", () => {
  test("numbers the cases in the order they are listed", () => {
    const html = render(EXAMPLES);
    expect(html).toContain('<span class="example-number">Case 1</span>');
    expect(html).toContain('<span class="example-number">Case 2</span>');
    expect(html.indexOf("Case 1")).toBeLessThan(html.indexOf("Is Svalbard getting warmer?"));
    expect(html.indexOf("Is Svalbard getting warmer?")).toBeLessThan(html.indexOf("Case 2"));
  });

  test("links each case to its page", () => {
    expect(render(EXAMPLES)).toContain('href="/case?v=air_temp&amp;p=78.22,15.65');
  });

  test("holds a pin for the string on each card when the examples are on the globe", () => {
    expect(
      render(EXAMPLES, true).match(/<span class="example-tack" aria-hidden="true"><\/span>/g),
    ).toHaveLength(2);
    expect(render(EXAMPLES)).not.toContain("example-tack");
  });

  test("marks each entry with its number, so a pin on the globe can find its card", () => {
    const html = render(EXAMPLES, true);
    expect(html).toContain('<li data-example="1"><a class="example-card"');
    expect(html).toContain('<li data-example="2"><a class="example-card"');
  });

  test("draws no string until an example is singled out", () => {
    expect(render(EXAMPLES, true)).not.toContain("case-string");
  });

  test("shows nothing when there is no example", () => {
    expect(render([])).toBe("");
  });
});
