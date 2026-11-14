import type { JSX } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, test, vi } from "vitest";
import type { PlaceCandidate } from "../api";
import { EMPTY_DRAFT, placeFromCandidate } from "../caseDraft";
import type { PlaceAction } from "../caseDraft";
import type { CasePlace } from "../caseUrl";
import { GLOBE_UNAVAILABLE, GlobeContext } from "../globeContext";
import { CaseSettings } from "./CaseSettings";

type ChooseFromSearch = (action: PlaceAction, place: CasePlace, candidate: PlaceCandidate) => void;

// The place search asks the API and needs clicks. The stand-in keeps its choose handler, so a
// test can choose a search result.
const search = vi.hoisted((): { onChoose: ChooseFromSearch | undefined } => ({ onChoose: undefined }));
vi.mock("./PlaceSearch", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./PlaceSearch")>()),
  PlaceSearch: (props: { onChoose: ChooseFromSearch }) => {
    search.onChoose = props.onChoose;
    return null;
  },
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
  search.onChoose = undefined;
});

function emptySettings(): JSX.Element {
  return (
    <CaseSettings
      draft={EMPTY_DRAFT}
      variables={{ status: "idle" }}
      pending={true}
      onPickCandidate={() => undefined}
      onChange={() => undefined}
      onRun={() => undefined}
    />
  );
}

describe("CaseSettings", () => {
  test("passes a place chosen from the place search to onPickCandidate", () => {
    const picked: PlaceCandidate[] = [];
    renderToStaticMarkup(
      <CaseSettings
        draft={EMPTY_DRAFT}
        variables={{ status: "idle" }}
        pending={true}
        onPickCandidate={(candidate) => picked.push(candidate)}
        onChange={() => undefined}
        onRun={() => undefined}
      />,
    );
    search.onChoose?.("use", placeFromCandidate(SHANGHAI), SHANGHAI);
    expect(picked).toEqual([SHANGHAI]);
  });

  test("offers a click on the globe as a way to choose the first place", () => {
    const html = renderToStaticMarkup(emptySettings());
    expect(html).toContain("No place yet. Search for one below, or click the globe.");
  });

  test("offers only the place search when the globe could not start", () => {
    const html = renderToStaticMarkup(
      <GlobeContext value={GLOBE_UNAVAILABLE}>{emptySettings()}</GlobeContext>,
    );
    expect(html).toContain("No place yet. Search for one below.");
    expect(html).not.toContain("click the globe");
  });
});
