import { useEffect, useMemo, useState } from "react";
import type { JSX } from "react";
import type { ExampleCase } from "../api";
import { examplePins, pointedExample } from "../examplePins";
import type { ExampleLink, ExamplePin } from "../examplePins";
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
   * or with keyboard focus is singled out there (spec 3, "The globe").
   */
  onGlobe?: boolean;
}

const NO_PINS: readonly ExamplePin[] = [];
// How long the pointer rests on a card before the Earth turns to its example, so that a pointer
// only passing over the list moves nothing.
const HOVER_INTENT_MS = 200;

/** Ready-made cases that teach by showing (spec 3). They open from the cache, without NASA. */
export function ExampleCases({ examples, onOpen, onGlobe = false }: ExampleCasesProps): JSX.Element | null {
  const list = examples.status === "done" ? examples.value : null;
  const pins = useMemo(() => (onGlobe && list !== null ? examplePins(list) : NO_PINS), [onGlobe, list]);
  const [linked, setLinked] = useState<ExampleLink | null>(null);
  // The number of the card the pointer is on, which singles its example out after a moment.
  const [pointed, setPointed] = useState<number | null>(null);
  useGlobeExamples(pins, {
    onOpen: (pin) => onOpen(pin.url),
    onPoint: (pin) => setLinked((current) => pointedExample(current, pin)),
  });
  useLinkedExample(onGlobe ? linked : null);

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
    <ul className="example-list">
      {list.map((example, index) => {
        const url = examplePageUrl(example.query);
        const number = index + 1;
        return (
          <li key={example.query}>
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
            </a>
          </li>
        );
      })}
    </ul>
  );
}

/** Singles out the linked example on the globe for as long as it is linked; null links none. */
function useLinkedExample(linked: ExampleLink | null): void {
  const { handle } = useGlobe();
  const number = linked?.number ?? null;
  const turn = linked?.turn ?? false;

  useEffect(() => {
    if (handle === null || number === null) return;
    handle.linkExample({ number, turn });
    return () => handle.linkExample(null);
  }, [handle, number, turn]);
}
