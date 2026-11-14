import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../api";
import type { ExampleCase, TrendMap } from "../api";
import { DEFINITIONS } from "../definitions";
import type { RequestState } from "../useRequest";
import { RegionView } from "./RegionView";
import { AIR_TEMP, TREND_MAP } from "./testData";

// The map's request answers with whatever the test sets here, so nothing touches the network.
const request = vi.hoisted((): { state: RequestState<TrendMap> } => ({ state: { status: "idle" } }));
vi.mock("../useRequest", () => ({ useRequest: () => ({ state: request.state, retry: () => undefined }) }));

const QUERY = "v=air_temp&box=55,20,65,30&from=1981&to=2025&s=annual";
const EXAMPLES: ExampleCase[] = [
  {
    title: "Is Svalbard getting warmer?",
    teaser: "Air temperature in Longyearbyen.",
    query: "v=air_temp&p=78.22,15.65",
  },
];

function renderRegionView(): string {
  return renderToStaticMarkup(
    <RegionView
      query={QUERY}
      variables={{ status: "done", value: [AIR_TEMP] }}
      examples={{ status: "done", value: EXAMPLES }}
      preloaded={null}
      notes={null}
      onOpenPage={() => undefined}
      onShowMap={() => undefined}
      onNormalised={() => undefined}
    />,
  );
}

beforeEach(() => {
  request.state = { status: "idle" };
});

describe("RegionView", () => {
  test("withholds sharing while the previous map is shown during loading", () => {
    request.state = { status: "loading", stale: TREND_MAP };
    const html = renderRegionView();
    expect(html).toContain("Verdict for the whole box");
    expect(html).not.toContain("Copy link");
  });

  test("defines the words its verdict and table use, as the case evidence does", () => {
    request.state = { status: "done", value: TREND_MAP };
    const html = renderRegionView();
    for (const { definition } of DEFINITIONS) expect(html).toContain(definition);
    expect(html).toContain(AIR_TEMP.definition);
  });

  test("holds the verdict first, then the map settings, then the map, the order on screen", () => {
    request.state = { status: "done", value: TREND_MAP };
    const html = renderRegionView();
    const verdict = html.indexOf("Verdict for the whole box");
    const settings = html.indexOf("Map settings");
    const map = html.indexOf("Trend in each grid cell");
    expect(verdict).toBeGreaterThanOrEqual(0);
    expect(verdict).toBeLessThan(settings);
    expect(settings).toBeLessThan(map);
  });

  test("gives the verdict sentence before the note on how the box was averaged", () => {
    request.state = { status: "done", value: TREND_MAP };
    const html = renderRegionView();
    const sentence = html.indexOf(TREND_MAP.area_mean.verdict.sentence);
    expect(sentence).toBeGreaterThanOrEqual(0);
    expect(html.indexOf("All the grid cells averaged into one series")).toBeGreaterThan(sentence);
  });

  test("folds the map settings behind a button once a map is on screen", () => {
    request.state = { status: "done", value: TREND_MAP };
    const html = renderRegionView();
    expect(html).toContain("Change this map");
    expect(html).toContain('aria-expanded="false"');
  });

  test("shows the map settings unfolded when the map cannot be made", () => {
    request.state = { status: "failed", error: new ApiError("bad_place", "The box is too large.", 400) };
    expect(renderRegionView()).not.toContain("Change this map");
  });

  test("says that the globe draws the cells", () => {
    request.state = { status: "done", value: TREND_MAP };
    expect(renderRegionView()).toContain(
      "Air temperature from 1981 to 2025, all months, coloured on the globe. Click a cell to open it as a case.",
    );
  });

  test("offers the saved example cases when NASA's data service is not answering", () => {
    request.state = {
      status: "failed",
      error: new ApiError("source_unavailable", "NASA POWER did not answer.", 502),
    };
    const html = renderRegionView();
    expect(html).toContain("NASA POWER did not answer.");
    expect(html).toContain("Try again");
    expect(html).toContain("Is Svalbard getting warmer?");
  });

  test("offers no examples for an error that changing the settings fixes", () => {
    request.state = { status: "failed", error: new ApiError("bad_place", "The box is too large.", 400) };
    const html = renderRegionView();
    expect(html).toContain("The box is too large.");
    expect(html).not.toContain("Is Svalbard getting warmer?");
  });
});
