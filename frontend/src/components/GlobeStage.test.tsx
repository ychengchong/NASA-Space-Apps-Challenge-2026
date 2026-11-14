import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { GLOBE_UNAVAILABLE, GlobeContext } from "../globeContext";
import type { GlobeState } from "../globeContext";
import { GlobeStage } from "./GlobeStage";
import type { StageHint } from "./GlobeStage";

const HINT: StageHint = {
  pointer: "Drag to turn the Earth. Click it to pick a point.",
  touch: "Turn with two fingers. Tap to pick a point.",
};

function renderStage(state?: GlobeState, pick: ReactNode = null): string {
  const stage = (
    <GlobeStage stageRef={{ current: null }} hint={HINT} pick={pick} noteRef={() => undefined}>
      <div>canvas</div>
    </GlobeStage>
  );
  return renderToStaticMarkup(
    state === undefined ? stage : <GlobeContext value={state}>{stage}</GlobeContext>,
  );
}

describe("GlobeStage", () => {
  test("draws the ring of degree marks hidden, for the globe to size and show", () => {
    const html = renderStage();
    expect(html).toContain('<div class="stage-ring" aria-hidden="true" hidden="">');
    // A mark every 5 degrees, the longest every 30.
    expect(html.match(/<line /g)).toHaveLength(72);
    expect(html.match(/class="stage-ring-long"/g)).toHaveLength(12);
  });

  test("names its controls for screen readers, and waits for the globe before taking a press", () => {
    const html = renderStage();
    for (const label of ["Zoom in", "Zoom out", "Show the whole Earth"]) {
      expect(html).toContain(`aria-label="${label}" disabled=""`);
    }
  });

  test("says what the globe does, for a pointer and for a finger", () => {
    const html = renderStage();
    expect(html).toContain(HINT.pointer);
    expect(html).toContain(HINT.touch);
  });

  test("shows the choices for a picked point in place of the hint, right after the globe", () => {
    const html = renderStage(undefined, <button type="button">Use this place</button>);
    expect(html).toContain("Use this place");
    expect(html).not.toContain(HINT.pointer);
    expect(html.indexOf("Use this place")).toBeLessThan(html.indexOf("Zoom in"));
  });

  test("keeps a place for a view's caption or key", () => {
    expect(renderStage()).toContain('class="stage-note"');
  });

  test("credits the makers of the globe's tiles", () => {
    const html = renderStage();
    expect(html).toContain("OpenFreeMap");
    expect(html).toContain("© OpenMapTiles");
    expect(html).toContain("OpenStreetMap");
  });

  test("says what still works when the browser cannot draw the globe", () => {
    const html = renderStage(GLOBE_UNAVAILABLE);
    expect(html).toContain("The globe could not start, because this browser has no WebGL.");
    expect(html).not.toContain("<button");
    expect(html).not.toContain(HINT.pointer);
    expect(html).not.toContain('class="stage-note"');
    expect(html).toContain("OpenStreetMap");
  });
});
