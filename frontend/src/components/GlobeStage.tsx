import type { JSX, ReactNode, Ref, RefObject } from "react";
import { useGlobe } from "../globeContext";
import { RING_REACH } from "../globeGeometry";

const ZOOM_STEP = 1;

// The ring of degree marks is drawn in units of a hundredth of the Earth's radius, so the
// stylesheet can size it to the Earth's disc (styles.css, .stage-ring).
const RING_EARTH_RADIUS = 100;
const RING_VIEW = RING_EARTH_RADIUS * RING_REACH;
// A full circle a little outside the Earth, a fine one further out, and a mark every 5° between
// them: longer at every 10° and longest, past the outer circle, at every 30°.
const RING_INNER = 101.8;
const RING_OUTER = 105.8;
const RING_SHORT_MARK = 103.8;
const RING_LONG_MARK = 108.7;
const RING_MARK_STEP = 5;
const RING_MEDIUM_STEP = 10;
const RING_LONG_STEP = 30;
const FULL_TURN = 360;
const DEGREES_TO_RADIANS = Math.PI / 180;

/** One line on what the globe does on a screen, as it reads with a pointer and with a finger. */
export interface StageHint {
  pointer: string;
  /** Shown on a phone, where one finger scrolls the page and two move the globe. */
  touch: string;
}

interface GlobeStageProps {
  /** Given to the stage's element, which the globe centres the Earth in. */
  stageRef: RefObject<HTMLElement | null>;
  hint: StageHint;
  /** The point the user picked, with what to do with it; it takes the hint's place. */
  pick: ReactNode;
  /** Given to the element where a view draws its caption or its key (see StageNote). */
  noteRef: Ref<HTMLDivElement>;
  /** The globe's canvas, which loads after the first paint. */
  children: ReactNode;
}

/**
 * The part of the screen the globe is seen through (spec 3, "The globe"): beside the case file
 * from 640px, above it on a phone. The globe itself fills the whole screen behind the page; the
 * stage holds its controls, its hint, the choices for a picked point, a view's caption or key,
 * and the credit for its tiles.
 */
export function GlobeStage({ stageRef, hint, pick, noteRef, children }: GlobeStageProps): JSX.Element {
  const { handle, status } = useGlobe();
  return (
    <section className="stage" ref={stageRef} aria-label="Globe" tabIndex={-1}>
      <div className="stage-globe">{children}</div>
      <StageRing />
      {status === "unavailable" ? (
        <p className="stage-notice">
          The globe could not start, because this browser has no WebGL. Everything else works: search for a
          place in the case settings, and type the edges of a region&apos;s box in the map settings.
        </p>
      ) : (
        <>
          {/* A live region right after the globe: a picked point is announced, and Tab reaches
              its choices straight from the globe. */}
          <div className="stage-top" aria-live="polite">
            {pick ?? (
              <p className="stage-hint">
                <span className="stage-hint-pointer">{hint.pointer}</span>
                <span className="stage-hint-touch">{hint.touch}</span>
              </p>
            )}
          </div>
          <span className="stage-crosshair" aria-hidden="true" />
          <div className="stage-controls">
            <button
              type="button"
              className="stage-button"
              aria-label="Zoom in"
              disabled={handle === null}
              onClick={() => handle?.zoomBy(ZOOM_STEP)}
            >
              <span aria-hidden="true">+</span>
            </button>
            <button
              type="button"
              className="stage-button"
              aria-label="Zoom out"
              disabled={handle === null}
              onClick={() => handle?.zoomBy(-ZOOM_STEP)}
            >
              <span aria-hidden="true">−</span>
            </button>
            <button
              type="button"
              className="stage-button"
              aria-label="Show the whole Earth"
              disabled={handle === null}
              onClick={() => handle?.showEarth()}
            >
              <EarthIcon />
            </button>
          </div>
          <div className="stage-note" ref={noteRef} />
        </>
      )}
      <p className="stage-credit">
        <a href="https://openfreemap.org">OpenFreeMap</a>{" "}
        <a href="https://www.openmaptiles.org/">© OpenMapTiles</a> Data from{" "}
        <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>
      </p>
    </section>
  );
}

/**
 * The ring of degree marks round the whole Earth, as round a hemisphere in an atlas. It is
 * decoration: the globe sizes it to the Earth's disc and shows it while the whole Earth is in
 * view, so it starts hidden.
 */
export function StageRing(): JSX.Element {
  const marks: JSX.Element[] = [];
  for (let angle = 0; angle < FULL_TURN; angle += RING_MARK_STEP) {
    const long = angle % RING_LONG_STEP === 0;
    const reach = long ? RING_LONG_MARK : angle % RING_MEDIUM_STEP === 0 ? RING_OUTER : RING_SHORT_MARK;
    const cos = Math.cos(angle * DEGREES_TO_RADIANS);
    const sin = Math.sin(angle * DEGREES_TO_RADIANS);
    marks.push(
      <line
        key={angle}
        className={long ? "stage-ring-long" : undefined}
        x1={(cos * RING_INNER).toFixed(2)}
        y1={(sin * RING_INNER).toFixed(2)}
        x2={(cos * reach).toFixed(2)}
        y2={(sin * reach).toFixed(2)}
      />,
    );
  }
  return (
    <div className="stage-ring" aria-hidden="true" hidden>
      <svg viewBox={`${-RING_VIEW} ${-RING_VIEW} ${2 * RING_VIEW} ${2 * RING_VIEW}`} focusable="false">
        <circle className="stage-ring-inner" r={RING_INNER} />
        <circle r={RING_OUTER} />
        {marks}
      </svg>
    </div>
  );
}

/** A circle with an equator and a meridian: the whole Earth. */
function EarthIcon(): JSX.Element {
  return (
    <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="10" cy="10" r="7.5" />
        <ellipse cx="10" cy="10" rx="3.2" ry="7.5" />
        <path d="M2.5 10h15" />
      </g>
    </svg>
  );
}
