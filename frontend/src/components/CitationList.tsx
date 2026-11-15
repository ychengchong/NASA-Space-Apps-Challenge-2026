import type { JSX } from "react";
import type { Citation } from "../api";
import { citationHref, citationLabel } from "../citations";

/**
 * The reviewed sources an AI text cites (spec 8): publisher, title and section as a link to the
 * manifest's address, a mark on the project's own notes, and the cited passage behind a
 * disclosure. Everything is plain text; nothing here is read as HTML.
 */
export function CitationList({ citations }: { citations: readonly Citation[] }): JSX.Element | null {
  if (citations.length === 0) return null;
  return (
    <ul className="citation-list" aria-label="Sources">
      {citations.map((citation) => (
        <CitationItem key={`${citation.source_id}/${citation.section_id}`} citation={citation} />
      ))}
    </ul>
  );
}

function CitationItem({ citation }: { citation: Citation }): JSX.Element {
  const label = citationLabel(citation);
  const href = citationHref(citation);
  return (
    <li className="citation">
      <span className="citation-source">
        {href === null ? (
          label
        ) : (
          // A new tab keeps the AI's answer on screen while the source is read.
          <a href={href} target="_blank" rel="noopener noreferrer">
            {label}
            <span className="visually-hidden"> (opens in a new tab)</span>
          </a>
        )}
        {citation.kind === "project" ? (
          <span className="citation-kind"> · a note by this project, not by NASA</span>
        ) : null}
      </span>
      <details className="disclosure citation-passage">
        <summary>Show the cited passage</summary>
        <blockquote className="citation-text">{citation.passage}</blockquote>
      </details>
    </li>
  );
}
