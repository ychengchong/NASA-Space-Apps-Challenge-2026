import { useState } from "react";
import type { JSX, MouseEvent, ReactNode } from "react";
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
  /** Further ways on, set under the links of "Explore further": the other variables to test. */
  more?: ReactNode;
}

type CopyState = "idle" | "copied" | "failed";

/**
 * What to do with an answer, right under it (spec 3): copy the link that holds the whole case or
 * map, and, for a case, every way on to another page in one "Explore further" sheet. Give it the
 * case or the map as its key, so a new answer starts without the last one's "Link copied".
 */
export function CaseActions({ subject, region, overview, world, more }: CaseActionsProps): JSX.Element {
  return (
    <div className="case-actions">
      <CopyLink subject={subject} />
      <ExploreFurther region={region} overview={overview} world={world} more={more} />
    </div>
  );
}

/**
 * "Copy link" and the line that says whether it worked. Give it the case or the map as its key,
 * so a new answer starts without the last one's "Link copied".
 */
export function CopyLink({ subject }: { subject: "case" | "map" }): JSX.Element {
  const [copy, setCopy] = useState<CopyState>("idle");
  const copyLink = (): void => {
    void copyText(window.location.href).then((copied) => setCopy(copied ? "copied" : "failed"));
  };
  return (
    <>
      <p className="case-actions-row">
        <button type="button" className="button button-secondary" onClick={copyLink}>
          Copy link
        </button>
      </p>
      <p className="status-text" role="status">
        {copyStatusText(copy, subject)}
      </p>
    </>
  );
}

type ExploreFurtherProps = Omit<CaseActionsProps, "subject">;

/** The "Explore further" sheet: the ways on to other pages, then `more`. Nothing without a way on. */
export function ExploreFurther({ region, overview, world, more }: ExploreFurtherProps): JSX.Element | null {
  const cards = exploreCards(region, overview, world);
  if (cards.length === 0) return null;
  return (
    <nav className="panel sheet explore" aria-labelledby="explore-heading">
      <h2 id="explore-heading">Explore further</h2>
      <ul className="explore-list">
        {cards.map((card) => (
          <li key={card.title}>
            <a className="explore-card" href={card.href} onClick={card.onClick}>
              <span className="explore-title">
                {card.title} <span aria-hidden="true">→</span>
              </span>
              <span className="explore-hint">{card.hint}</span>
            </a>
          </li>
        ))}
      </ul>
      {more}
    </nav>
  );
}

interface ExploreCard {
  title: string;
  hint: string;
  href: string;
  onClick: (event: MouseEvent<HTMLAnchorElement>) => void;
}

/**
 * The ways on from an answer that open a page of their own, most used first. The seasons and
 * the period are folded panels of the case's own page, so they are not repeated here.
 */
function exploreCards(
  region: RegionLink | undefined,
  overview: RegionLink | undefined,
  world: RegionLink | undefined,
): ExploreCard[] {
  const cards: ExploreCard[] = [];
  if (overview !== undefined) {
    cards.push(
      pageCard("What is changing here?", `The rate of every variable at ${overview.placeName}.`, overview),
    );
  }
  if (world !== undefined) {
    cards.push(
      pageCard(
        "The whole world",
        "The same variable, period and season averaged over a world sample.",
        world,
      ),
    );
  }
  if (region !== undefined) {
    cards.push(
      pageCard(
        "Map this region",
        `A map that shows the rate of change in every grid cell of a 10° by 10° box around ${region.placeName}. Significance is not assessed for the map.`,
        region,
      ),
    );
  }
  return cards;
}

function pageCard(title: string, hint: string, link: RegionLink): ExploreCard {
  return { title, hint, href: link.url, onClick: (event) => followInApp(event, link.url, link.onOpenPage) };
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
