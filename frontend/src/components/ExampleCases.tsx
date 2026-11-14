import { useEffect, useMemo, useRef, useState } from "react";
import type { JSX } from "react";
import type { ExampleCase } from "../api";
import { examplePins, pointedExample, stringPath } from "../examplePins";
import type { ExamplePin, LinkedExample, ScreenPoint } from "../examplePins";
import { useGlobe, useGlobeExamples } from "../globeContext";
import { followInApp } from "../links";
import { examplePageUrl } from "../route";
import type { RequestState } from "../useRequest";

interface ExampleCasesProps {
  examples: RequestState<ExampleCase[]>;
  /** Opens an example inside the app; `url` is its case page. */
  onOpen: (url: string) => void;
  /**
   * On the first screen the examples are also pinned to the globe, and the one under the pointer
   * or with keyboard focus is tied to its pins with a string (spec 3, "The globe").
   */
  onGlobe?: boolean;
}

/** The string of one example: from the pin on its card to each of its pins on the globe. */
interface StringEnds {
  /** The number of the example the string belongs to. */
  number: number;
  from: ScreenPoint;
  /** One end for each of the case's places; null for a pin on the far side of the Earth. */
  to: readonly (ScreenPoint | null)[];
}

const NO_PINS: readonly ExamplePin[] = [];
const TACK_SELECTOR = ".example-tack";
// How long the pointer rests on a card before the Earth turns to its example, so that a pointer
// only passing over the list moves nothing.
const HOVER_INTENT_MS = 200;

/** Ready-made cases that teach by showing (spec 3). They open from the cache, without NASA. */
export function ExampleCases({ examples, onOpen, onGlobe = false }: ExampleCasesProps): JSX.Element | null {
  const list = examples.status === "done" ? examples.value : null;
  const pins = useMemo(() => (onGlobe && list !== null ? examplePins(list) : NO_PINS), [onGlobe, list]);
  const [linked, setLinked] = useState<LinkedExample | null>(null);
  // The number of the card the pointer is on, which singles its example out after a moment.
  const [pointed, setPointed] = useState<number | null>(null);
  const cards = useRef<HTMLUListElement | null>(null);
  useGlobeExamples(pins, {
    onOpen: (pin) => onOpen(pin.url),
    onPoint: (pin) => setLinked((current) => pointedExample(current, pin)),
  });
  const ends = useExampleString(onGlobe ? linked : null, cards);

  useEffect(() => {
    if (pointed === null) return;
    const timer = window.setTimeout(() => setLinked({ number: pointed, turn: true }), HOVER_INTENT_MS);
    return () => window.clearTimeout(timer);
  }, [pointed]);

  if (examples.status === "loading") return <p className="status-text">Loading the example cases…</p>;
  if (examples.status === "failed") {
    return <p className="status-text">The example cases could not be loaded. {examples.error.message}</p>;
  }
  if (list === null || list.length === 0) return null;

  const unlink = (number: number): void => {
    setPointed((current) => (current === number ? null : current));
    setLinked((current) => (current?.number === number ? null : current));
  };
  return (
    <>
      <ul className="example-list" ref={cards}>
        {list.map((example, index) => {
          const url = examplePageUrl(example.query);
          const number = index + 1;
          return (
            <li key={example.query} data-example={number}>
              <a
                className={linked?.number === number ? "example-card is-linked" : "example-card"}
                href={url}
                onClick={(event) => followInApp(event, url, onOpen)}
                onMouseEnter={() => setPointed(number)}
                onMouseLeave={() => unlink(number)}
                // Focus is deliberate, so it singles the example out at once.
                onFocus={() => setLinked({ number, turn: true })}
                onBlur={() => unlink(number)}
              >
                <span className="example-number">Case {number}</span>
                <span className="example-title">{example.title}</span>
                <span className="example-teaser">{example.teaser}</span>
                {onGlobe ? <span className="example-tack" aria-hidden="true" /> : null}
              </a>
            </li>
          );
        })}
      </ul>
      {ends !== null ? <CaseString ends={ends} /> : null}
    </>
  );
}

/**
 * Singles out the linked example on the globe, and returns the ends of its string: the pin on
 * its card in the list `cards`, measured whenever the globe or the page moves, and its pins on
 * the globe. Null while no example is singled out, and before the globe has answered.
 */
function useExampleString(
  linked: LinkedExample | null,
  cards: { current: HTMLElement | null },
): StringEnds | null {
  const { handle } = useGlobe();
  const [ends, setEnds] = useState<StringEnds | null>(null);
  const number = linked?.number ?? null;
  const turn = linked?.turn ?? false;

  useEffect(() => {
    if (handle === null || number === null) return;
    let pins: readonly (ScreenPoint | null)[] = [];
    const draw = (): void => {
      const tack = cards.current?.querySelector(`[data-example="${number}"] ${TACK_SELECTOR}`);
      const card = tack?.getBoundingClientRect();
      if (card === undefined) return;
      const from = { x: card.left + card.width / 2, y: card.top + card.height / 2 };
      setEnds({ number, from, to: pins });
    };
    handle.linkExample({
      number,
      turn,
      onMove: (points) => {
        pins = points;
        draw();
      },
    });
    window.addEventListener("scroll", draw, { passive: true });
    window.addEventListener("resize", draw);
    return () => {
      handle.linkExample(null);
      window.removeEventListener("scroll", draw);
      window.removeEventListener("resize", draw);
    };
  }, [handle, number, turn, cards]);

  // The ends of an example that is no longer singled out are not drawn.
  return ends !== null && ends.number === number ? ends : null;
}

/**
 * The red string from the example's card to its pins, drawn over the whole screen. It is
 * decoration: the card's number and the pin's tag say the same.
 */
function CaseString({ ends }: { ends: StringEnds }): JSX.Element {
  return (
    <svg className="case-string" aria-hidden="true" focusable="false">
      {ends.to.map((to, index) =>
        to === null ? null : (
          <g key={index}>
            <path className="case-string-shadow" d={stringPath(ends.from, to)} transform="translate(2 7)" />
            <path className="case-string-thread" d={stringPath(ends.from, to)} />
          </g>
        ),
      )}
    </svg>
  );
}
