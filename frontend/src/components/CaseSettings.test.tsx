import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, test, vi } from "vitest";
import type { PlaceCandidate } from "../api";
import { EMPTY_DRAFT, placeFromCandidate } from "../caseDraft";
import type { PlaceAction } from "../caseDraft";
import type { CasePlace } from "../caseUrl";
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

describe("CaseSettings", () => {
  test("passes a place chosen from the place search to onPickCandidate", () => {
    const picked: PlaceCandidate[] = [];
    renderToStaticMarkup(
      <CaseSettings
        draft={EMPTY_DRAFT}
        variables={{ status: "idle" }}
        pending={true}
        pickedPoint={null}
        onDismissPickedPoint={() => undefined}
        onPickCandidate={(candidate) => picked.push(candidate)}
        onChange={() => undefined}
        onRun={() => undefined}
      />,
    );
    search.onChoose?.("use", placeFromCandidate(SHANGHAI), SHANGHAI);
    expect(picked).toEqual([SHANGHAI]);
  });
});
