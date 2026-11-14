import type { JSX } from "react";
import type { ExampleCase } from "../api";
import { followInApp } from "../links";
import { examplePageUrl } from "../route";
import type { RequestState } from "../useRequest";

interface ExampleCasesProps {
  examples: RequestState<ExampleCase[]>;
  /** Opens an example inside the app; `url` is its case page. */
  onOpen: (url: string) => void;
}

/** Ready-made cases that teach by showing (spec 3). They open from the cache, without NASA. */
export function ExampleCases({ examples, onOpen }: ExampleCasesProps): JSX.Element | null {
  if (examples.status === "loading") return <p className="status-text">Loading the example cases…</p>;
  if (examples.status === "failed") {
    return <p className="status-text">The example cases could not be loaded. {examples.error.message}</p>;
  }
  if (examples.status !== "done" || examples.value.length === 0) return null;
  return (
    <ul className="example-list">
      {examples.value.map((example) => {
        const url = examplePageUrl(example.query);
        return (
          <li key={example.query}>
            <a className="example-card" href={url} onClick={(event) => followInApp(event, url, onOpen)}>
              <span className="example-title">{example.title}</span>
              <span className="example-teaser">{example.teaser}</span>
            </a>
          </li>
        );
      })}
    </ul>
  );
}
