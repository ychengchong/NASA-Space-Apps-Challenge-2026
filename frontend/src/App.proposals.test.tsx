import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "./App";
import { proposeCase } from "./api";
import type { AiHelper } from "./components/QuestionBar";
import { AIR_TEMP } from "./components/testData";
import type { KeywordProposal } from "./keywordMatch";

const captured = vi.hoisted(() => ({
  onProposal: null as null | ((proposal: KeywordProposal) => void),
  ai: undefined as AiHelper | undefined,
}));

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  proposeCase: vi.fn(),
}));
vi.mock("./useRequest", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./useRequest")>()),
  useRequest: (key: string | null) => ({
    state:
      key === "capabilities" ? { status: "done", value: { ai_planner_available: true } } : { status: "idle" },
    retry: () => undefined,
  }),
}));
vi.mock("./components/QuestionBar", () => ({
  QuestionBar: (props: { onProposal: (proposal: KeywordProposal) => void; ai?: AiHelper }) => {
    captured.onProposal = props.onProposal;
    captured.ai = props.ai;
    return null;
  },
}));
vi.mock("./components/GlobeCanvas", () => ({ default: () => null }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  captured.onProposal = null;
  captured.ai = undefined;
});

describe.each([
  ["/place", "?p=60.17,24.94"],
  ["/world", "?v=air_temp"],
])("proposals from %s", (pathname, search) => {
  function openPage(): ReturnType<typeof vi.fn> {
    const pushState = vi.fn();
    vi.stubGlobal("window", { location: { pathname, search }, history: { pushState } });
    const html = renderToStaticMarkup(<App />);
    expect(html).not.toContain('id="settings-heading"');
    return pushState;
  }

  test("opens the settings page for a keyword proposal", () => {
    const pushState = openPage();
    expect(captured.onProposal).not.toBeNull();
    captured.onProposal?.({ variables: [AIR_TEMP], places: [] });
    expect(pushState).toHaveBeenCalledWith(null, "", "/");
  });

  test("opens the settings page for an AI proposal", async () => {
    const pushState = openPage();
    vi.mocked(proposeCase).mockResolvedValue({
      variables: [AIR_TEMP],
      places: [],
      from: 1981,
      to: 2025,
      season: "annual",
      notices: [],
      written_by_ai: true,
    });
    expect(captured.ai).toBeDefined();
    expect(await captured.ai?.ask("Is Helsinki getting warmer?")).toBe("answered");
    expect(pushState).toHaveBeenCalledWith(null, "", "/");
  });
});
