/**
 * How a citation reads on screen (spec 5, "Citation"). The server builds every citation from the
 * reviewed manifest, never from the AI's words; this only writes it out.
 */

import type { Citation } from "./api";

/**
 * "NASA Langley Research Center, POWER Project · POWER Data Methodology · Release History": the
 * publisher, the title and the section. A section the manifest names after its title, as in
 * "POWER Data Methodology: Release History", is not given the title twice, and a section that
 * only repeats the title is left out.
 */
export function citationLabel(citation: Citation): string {
  const { publisher, title } = citation;
  const prefix = `${title}: `;
  const section = citation.section.startsWith(prefix)
    ? citation.section.slice(prefix.length)
    : citation.section;
  const source = `${publisher} · ${title}`;
  return section === "" || section === title ? source : `${source} · ${section}`;
}

const HTTPS_LINK = /^https:\/\//i;

/**
 * The address a citation links to, or null when it is not an HTTPS address. The server allows
 * only HTTPS addresses from the manifest; this keeps any other scheme out of a link anyway.
 */
export function citationHref(citation: Citation): string | null {
  return HTTPS_LINK.test(citation.url) ? citation.url : null;
}
