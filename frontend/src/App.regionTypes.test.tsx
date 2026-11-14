import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { PlaceCandidate } from "./api";
import App from "./App";
import type { KeywordProposal } from "./keywordMatch";

// Every request stays idle, so nothing touches the network.
vi.mock("./useRequest", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./useRequest")>()),
  useRequest: () => ({ state: { status: "idle" }, retry: () => undefined }),
}));
// Leaflet needs a browser, and the maps are not under test.
vi.mock("./components/PlaceMap", () => ({ default: () => null }));
vi.mock("./components/RegionMap", () => ({ default: () => null }));

// The stand-ins keep the handlers App gives the question bar and the case settings, so a test can
// call them as a keyword match or a pick from the place search would, and see what App remembers.
const handlers = vi.hoisted(
  (): {
    onProposal: ((proposal: KeywordProposal) => void) | undefined;
    onPickCandidate: ((candidate: PlaceCandidate) => void) | undefined;
    remembered: PlaceCandidate[][];
  } => ({ onProposal: undefined, onPickCandidate: undefined, remembered: [] }),
);
vi.mock("./components/QuestionBar", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./components/QuestionBar")>()),
  QuestionBar: (props: { onProposal: (proposal: KeywordProposal) => void }) => {
    handlers.onProposal = props.onProposal;
    return null;
  },
}));
vi.mock("./components/CaseSettings", () => ({
  CaseSettings: (props: { onPickCandidate: (candidate: PlaceCandidate) => void }) => {
    handlers.onPickCandidate = props.onPickCandidate;
    return null;
  },
}));
vi.mock("./useRegionTypes", () => ({
  useRegionTypes: () => ({
    known: new Map(),
    remember: (candidates: readonly PlaceCandidate[]) => handlers.remembered.push([...candidates]),
  }),
}));

const SHANGHAI: PlaceCandidate = {
  name: "Shanghai",
  country: "China",
  lat: 31.2222,
  lon: 121.4581,
  kind: "city",
  region_type: "megacity",
};

beforeEach(() => {
  handlers.onProposal = undefined;
  handlers.onPickCandidate = undefined;
  handlers.remembered = [];
  vi.stubGlobal("window", { location: { pathname: "/", search: "" } });
  renderToStaticMarkup(<App />);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  test("remembers the region types of the places a keyword match finds", () => {
    handlers.onProposal?.({ variables: [], places: [SHANGHAI] });
    expect(handlers.remembered).toEqual([[SHANGHAI]]);
  });

  test("remembers the region type of a place picked from the place search", () => {
    handlers.onPickCandidate?.(SHANGHAI);
    expect(handlers.remembered).toEqual([[SHANGHAI]]);
  });
});
