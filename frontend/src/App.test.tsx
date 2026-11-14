import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { AiStatus, ExampleCase, Investigation } from "./api";
import App from "./App";
import { investigation, SIGNIFICANT_RISE } from "./components/testData";

// Every request stays idle, so nothing touches the network. A test may give the answer to the
// question whether the AI is on, the list of example cases, and the answer of a case.
const server = vi.hoisted(
  (): {
    aiStatus: AiStatus | null;
    caseLoading: boolean;
    examples: ExampleCase[] | null;
    investigation: Investigation | null;
  } => ({
    aiStatus: null,
    caseLoading: false,
    examples: null,
    investigation: null,
  }),
);
const START_KEYS = ["ai", "variables", "examples"];
vi.mock("./useRequest", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./useRequest")>()),
  useRequest: (key: string | null) => {
    const idle = { state: { status: "idle" }, retry: () => undefined };
    if (key === "ai" && server.aiStatus !== null) {
      return { ...idle, state: { status: "done", value: server.aiStatus } };
    }
    if (key === "examples" && server.examples !== null) {
      return { ...idle, state: { status: "done", value: server.examples } };
    }
    // Every other key is a case or a map.
    if (key === null || START_KEYS.includes(key)) return idle;
    if (server.caseLoading) return { ...idle, state: { status: "loading", stale: null } };
    if (server.investigation !== null) {
      return { ...idle, state: { status: "done", value: server.investigation } };
    }
    return idle;
  },
}));
// The globe needs WebGL, and it is not under test.
vi.mock("./components/GlobeCanvas", () => ({ default: () => null }));

afterEach(() => {
  vi.unstubAllGlobals();
  server.aiStatus = null;
  server.caseLoading = false;
  server.examples = null;
  server.investigation = null;
});

const SVALBARD: ExampleCase = {
  title: "Is Svalbard getting warmer?",
  teaser: "Air temperature in Longyearbyen.",
  query: "v=air_temp&p=78.22,15.65&label=Longyearbyen&from=1981&to=2025&s=annual",
};
const PIN_HINT = "Click a pin to open an example, or pick a point.";
const PICK_HINT = "Drag to turn the Earth. Click it to pick a point.";

function renderAt(pathname: string, search: string): string {
  vi.stubGlobal("window", { location: { pathname, search } });
  return renderToStaticMarkup(<App />);
}

describe("App", () => {
  test.each([
    ["the first screen", "/", ""],
    ["a case", "/case", "?v=air_temp&p=60.17,24.94&label=Helsinki"],
    ["a map", "/map", "?v=air_temp&box=55,20,65,30"],
    ["a link that opens nothing", "/case", "?p=60.17,24.94"],
  ])("has exactly one h1 on %s", (_page, pathname, search) => {
    const html = renderAt(pathname, search);
    expect(html.match(/<h1[\s>]/g)).toHaveLength(1);
  });

  test("holds the globe's stage after the case file, so Tab meets the verdict before the globe", () => {
    const html = renderAt("/case", "?v=air_temp&p=60.17,24.94&label=Helsinki");
    const main = html.indexOf('id="main"');
    const stage = html.indexOf('class="stage"');
    expect(main).toBeGreaterThanOrEqual(0);
    expect(stage).toBeGreaterThan(main);
    expect(html.indexOf("site-footer")).toBeGreaterThan(stage);
  });

  test("says on the first screen's stage that a pin opens an example, once the examples are pinned", () => {
    server.examples = [SVALBARD];
    const html = renderAt("/", "");
    expect(html).toContain(PIN_HINT);
    expect(html).not.toContain(PICK_HINT);
  });

  test("keeps the first screen's stage to picking a point while there is no example to pin", () => {
    expect(renderAt("/", "")).toContain(PICK_HINT);
    server.examples = [];
    expect(renderAt("/", "")).toContain(PICK_HINT);
  });

  test("does not speak of pins on a case, where no example is pinned", () => {
    server.examples = [SVALBARD];
    const html = renderAt("/case", "?v=air_temp&p=60.17,24.94&label=Helsinki");
    expect(html).toContain(PICK_HINT);
    expect(html).not.toContain(PIN_HINT);
  });

  test("gives each example on the first screen a pin for its string, and none elsewhere", () => {
    server.examples = [SVALBARD];
    expect(renderAt("/", "")).toContain('class="example-tack"');
    // A link that opens nothing lists the examples in its notice, without the globe's pins.
    expect(renderAt("/map", "?v=air_temp").match(/class="example-tack"/g)).toBeNull();
  });

  test("says an AI reads the question until the server has said whether the AI is on", () => {
    const html = renderAt("/", "");
    expect(html).toContain("An AI reads your question");
  });

  test("says an AI reads the question when the server's AI is on", () => {
    server.aiStatus = { on: true };
    const html = renderAt("/", "");
    expect(html).toContain("An AI reads your question");
  });

  test("says the AI helper is off from the start when the server's AI is off", () => {
    server.aiStatus = { on: false };
    const html = renderAt("/", "");
    expect(html).toContain("The AI helper is off.");
    expect(html).not.toContain("An AI reads your question");
  });

  test.each([
    ["the first screen", "/", "", true],
    ["a link that opens nothing", "/case", "?p=60.17,24.94", true],
    ["a case", "/case", "?v=air_temp&p=60.17,24.94&label=Helsinki", false],
    ["a map", "/map", "?v=air_temp&box=55,20,65,30", false],
  ])("shows the example prompts on %s: %s", (_page, pathname, search, shown) => {
    const html = renderAt(pathname, search);
    expect(html.includes("Is the Sahara getting hotter?")).toBe(shown);
  });

  test.each([
    ["the first screen", "/", "", false],
    ["a case", "/case", "?v=air_temp&p=60.17,24.94&label=Helsinki", true],
    ["a map", "/map", "?v=air_temp&box=55,20,65,30", true],
  ])(
    "lets the verdict lead on %s: the question bar steps back there: %s",
    (_page, pathname, search, quiet) => {
      const html = renderAt(pathname, search);
      expect(html.includes("question-bar is-quiet")).toBe(quiet);
    },
  );

  test.each([
    ["a case", "/case", "?v=air_temp&p=60.17,24.94&label=Helsinki"],
    ["a map", "/map", "?v=air_temp&box=55,20,65,30"],
  ])("holds the place of the verdict while %s loads for the first time", (_page, pathname, search) => {
    server.caseLoading = true;
    expect(renderAt(pathname, search)).toContain('class="panel skeleton"');
  });

  test("holds the place of the chart right under the verdict while a case loads", () => {
    server.caseLoading = true;
    const html = renderAt("/case", "?v=air_temp&p=60.17,24.94&label=Helsinki");
    expect(html.match(/class="panel skeleton"/g)).toHaveLength(2);
    expect(html.indexOf("skeleton-chart")).toBeLessThan(html.indexOf("Change this case"));
  });

  test("shows the chart right after the verdict, before what to do with the answer", () => {
    server.investigation = investigation(SIGNIFICANT_RISE);
    const html = renderAt("/case", "?v=air_temp&p=60.17,24.94&label=Helsinki");
    const chart = html.indexOf('id="chart-heading"');
    expect(chart).toBeGreaterThan(html.indexOf('id="verdict-heading"'));
    expect(html.indexOf('class="case-actions"')).toBeGreaterThan(chart);
    expect(html.indexOf("Change this case")).toBeGreaterThan(chart);
  });

  test("keeps the chart out of the region that is read aloud when the verdict arrives", () => {
    server.investigation = investigation(SIGNIFICANT_RISE);
    const html = renderAt("/case", "?v=air_temp&p=60.17,24.94&label=Helsinki");
    const live = html.slice(html.indexOf('aria-live="polite"'), html.indexOf('id="chart-heading"'));
    expect(live).toContain("</section></div></div>");
  });

  test("offers on the first screen a way to set up a case by hand, down to the settings", () => {
    const html = renderAt("/", "");
    expect(html).toContain('<a href="#settings-heading">set up a case by hand</a>');
    expect(html).toContain('id="settings-heading"');
    expect(renderAt("/case", "?v=air_temp&p=60.17,24.94&label=Helsinki")).not.toContain("by hand");
  });

  test("shows no placeholder on a page that is not loading", () => {
    const html = renderAt("/case", "?v=air_temp&p=60.17,24.94&label=Helsinki");
    expect(html).not.toContain("skeleton");
  });

  test("credits the makers of the globe's tiles in the footer", () => {
    const html = renderAt("/", "");
    const footer = html.slice(html.indexOf("site-footer"));
    for (const name of ["OpenFreeMap", "OpenMapTiles", "OpenStreetMap", "Natural Earth"]) {
      expect(footer).toContain(name);
    }
  });
});
