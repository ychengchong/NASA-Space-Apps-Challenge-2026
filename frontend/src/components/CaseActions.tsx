import { useState } from "react";
import type { JSX } from "react";
import { copyText } from "../clipboard";
import { followInApp } from "../links";

/** "Map this region": where the link leads, and the place its box is drawn around. */
export interface RegionLink {
  url: string;
  placeName: string;
  onOpenPage: (url: string) => void;
}

interface CaseActionsProps {
  /** What the page shows, as its link is described: a case or a map. */
  subject: "case" | "map";
  region?: RegionLink;
  /** "What is changing here?": every variable at the case's first place. */
  overview?: RegionLink;
  /** "The whole world": the same variable, period and season in the world sample. */
  world?: RegionLink;
}

type CopyState = "idle" | "copied" | "failed";

/**
 * What to do with an answer, right under it (spec 3): copy the link that holds the whole case or
 * map, and, for a case, map the region around its first place. Give it the case or the map as
 * its key, so a new answer starts without the last one's "Link copied".
 */
export function CaseActions({ subject, region, overview, world }: CaseActionsProps): JSX.Element {
  const [copy, setCopy] = useState<CopyState>("idle");
  const copyLink = (): void => {
    void copyText(window.location.href).then((copied) => setCopy(copied ? "copied" : "failed"));
  };
  return (
    <div className="case-actions">
      <p className="case-actions-row">
        <button type="button" className="button button-secondary" onClick={copyLink}>
          Copy link
        </button>
        {region !== undefined ? (
          <a
            className="button button-secondary"
            href={region.url}
            onClick={(event) => followInApp(event, region.url, region.onOpenPage)}
          >
            Map this region
          </a>
        ) : null}
        {overview !== undefined ? (
          <a
            className="button button-secondary"
            href={overview.url}
            onClick={(event) => followInApp(event, overview.url, overview.onOpenPage)}
          >
            What is changing here?
          </a>
        ) : null}
        {world !== undefined ? (
          <a
            className="button button-secondary"
            href={world.url}
            onClick={(event) => followInApp(event, world.url, world.onOpenPage)}
          >
            The whole world
          </a>
        ) : null}
      </p>
      <p className="status-text" role="status">
        {copyStatusText(copy, subject)}
      </p>
      {region !== undefined ? (
        <p className="field-hint">
          “Map this region” runs the same test in every grid cell of a 10° by 10° box around{" "}
          {region.placeName}.
        </p>
      ) : null}
      {overview !== undefined ? (
        <p className="field-hint">
          “What is changing here?” lists the descriptive rate of every variable at {overview.placeName}.
        </p>
      ) : null}
      {world !== undefined ? (
        <p className="field-hint">
          “The whole world” shows the same variable, period and season averaged over a fixed sample of grid
          points across the world.
        </p>
      ) : null}
    </div>
  );
}

function copyStatusText(copy: CopyState, subject: "case" | "map"): string {
  switch (copy) {
    case "idle":
      return "";
    case "copied":
      return `Link copied. Anyone who opens it sees this ${subject}.`;
    case "failed":
      return "The link could not be copied. Copy the address from the address bar instead.";
  }
}
