import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "./App";

// Every request stays idle, so nothing touches the network.
vi.mock("./useRequest", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./useRequest")>()),
  useRequest: () => ({ state: { status: "idle" }, retry: () => undefined }),
}));
// Leaflet needs a browser, and the maps are not under test.
vi.mock("./components/PlaceMap", () => ({ default: () => null }));
vi.mock("./components/RegionMap", () => ({ default: () => null }));

afterEach(() => {
  vi.unstubAllGlobals();
});

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
});
