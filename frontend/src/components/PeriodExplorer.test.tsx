import type { ClickPoint } from "plotly.js-basic-dist-min";
import { prerender } from "react-dom/static";
import { beforeEach, describe, expect, test, vi } from "vitest";
import type { Investigation } from "../api";
import type { CaseParams } from "../caseUrl";
import { casePageUrl } from "../route";
import type { RequestState } from "../useRequest";
import { PeriodExplorer } from "./PeriodExplorer";
import { investigation, SIGNIFICANT_RISE } from "./testData";

// The scan request answers with whatever the test sets here, so nothing touches the network.
const request = vi.hoisted((): { state: RequestState<Investigation> } => ({ state: { status: "idle" } }));
vi.mock("../useRequest", () => ({ useRequest: () => ({ state: request.state, retry: () => undefined }) }));
// Plotly needs a browser. The stand-in keeps the chart's click handler, so a test can choose a point.
const chart = vi.hoisted((): { onPointClick: ((point: ClickPoint) => void) | undefined } => ({
  onPointClick: undefined,
}));
vi.mock("./PlotlyChart", () => ({
  default: (props: { onPointClick?: (point: ClickPoint) => void }) => {
    chart.onPointClick = props.onPointClick;
    return null;
  },
}));

const HELSINKI_CASE: CaseParams = {
  variable: "air_temp",
  places: [{ lat: 60.17, lon: 24.94, name: "Helsinki" }],
  from: 1981,
  to: 2025,
  season: "JJA",
};

function scannedCase(): Investigation {
  const answer = investigation(SIGNIFICANT_RISE);
  const [result] = answer.results;
  if (result?.trend == null) throw new Error("The test case has no trend.");
  const scan = [
    { start: 1981, sen_slope: 0.5, mk_p: 0.001 },
    { start: 1990, sen_slope: 0.6, mk_p: 0.002 },
  ];
  return { ...answer, results: [{ ...result, trend: { ...result.trend, scan } }] };
}

beforeEach(() => {
  request.state = { status: "done", value: scannedCase() };
  chart.onPointClick = undefined;
});

describe("PeriodExplorer", () => {
  test("choosing a first year on the chart loads the case again from that year", async () => {
    const opened: CaseParams[] = [];
    // prerender waits for the lazily loaded chart, so its click handler is in place.
    await prerender(
      <PeriodExplorer
        params={HELSINKI_CASE}
        investigation={investigation(SIGNIFICANT_RISE)}
        onOpenCase={(params) => opened.push(params)}
      />,
    );
    chart.onPointClick?.({ x: 1990, y: 0.6, curveNumber: 0, pointIndex: 1 });
    expect(opened.map(casePageUrl)).toEqual([
      "/case?v=air_temp&p=60.17,24.94&label=Helsinki&from=1990&to=2025&s=JJA",
    ]);
  });
});
