"""Build the reviewed documentation corpus (spec 8, "Planned corpus and retrieval").

The reviewed list `data/corpus/sources.json` names NASA POWER and MERRA-2 documentation pages and
the project's own method notes in `data/corpus/project/`. The script fetches each page with a
timeout and a generic user agent, honours robots.txt, keeps the raw download outside the
repository, extracts the readable text, splits it into sections by headings and writes:

- `data/corpus/manifest.json`: the sources (with access date and content SHA-256), the sections
  (with length and SHA-256) and `corpus_version`, the SHA-256 of the rest of the manifest;
- `data/corpus/sections/{section_id}.txt`: one plain-text file per section.

If any source cannot be fetched the build stops and writes nothing: a source that is no longer
reachable is removed from the reviewed list by hand, never silently. Run from backend/:

    python -I scripts/build_corpus.py --accessed YYYY-MM-DD --raw-dir EMPTY_SCRATCH_DIR

The script uses the standard library only, so it runs under `python -I`.
"""

import argparse
import hashlib
import http.client
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

CORPUS_DIR = Path(__file__).resolve().parents[1] / "data" / "corpus"
SOURCES_FILE = "sources.json"
MANIFEST_FILE = "manifest.json"
SECTIONS_DIR = "sections"

# A generic client name: requests to outside services carry no project or personal details.
USER_AGENT = "Mozilla/5.0 (compatible; documentation-corpus-builder/1.0)"
FETCH_TIMEOUT_SECONDS = 30
# A pause between downloads, to stay a light visitor on the documentation servers.
DELAY_BETWEEN_FETCHES_SECONDS = 1.0
HTTP_OK = 200
# RFC 9309, 2.3.1.3: a robots.txt answered with a client error sets no rules.
HTTP_CLIENT_ERROR_MIN = 400
HTTP_CLIENT_ERROR_MAX = 499

# Section bounds (spec 8: sections short enough to retrieve, long enough to keep their context).
MIN_SECTION_CHARS = 200
MAX_SECTION_CHARS = 3_000

KIND_AGENCY = "agency"
KIND_PROJECT = "project"

# Elements whose whole subtree is page furniture, not documentation text.
DROPPED_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "nav",
        "header",
        "footer",
        "aside",
        "svg",
        "form",
        "button",
        "template",
        "iframe",
        "select",
        "dialog",
    }
)
# Classes dropped on every page: MkDocs heading permalinks, code line numbers and tab labels.
ALWAYS_DROPPED_CLASSES = frozenset({"headerlink", "linenos", "tabbed-labels"})
VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
# Tags that start or end a paragraph of text.
BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "li",
        "ul",
        "ol",
        "dl",
        "dt",
        "dd",
        "pre",
        "blockquote",
        "table",
        "thead",
        "tbody",
        "tr",
        "br",
        "hr",
        "figure",
        "figcaption",
        "details",
        "summary",
        "article",
        "main",
        "body",
    }
)
CELL_TAGS = frozenset({"td", "th"})
CELL_SEPARATOR = " | "
LIST_ITEM_PREFIX = "- "
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


class FetchError(Exception):
    """A source could not be downloaded."""


@dataclass(frozen=True)
class Response:
    """One HTTP response: status, media type and body bytes."""

    status: int
    content_type: str
    body: bytes


Fetcher = Callable[[str], Response]


@dataclass(frozen=True)
class Block:
    """One heading or paragraph of extracted text. `level` is 0 for a paragraph."""

    text: str
    level: int = 0


@dataclass(frozen=True)
class Section:
    """One retrievable section: its heading and its paragraphs."""

    title: str
    paragraphs: tuple[str, ...]

    @property
    def body(self) -> str:
        return "\n\n".join(self.paragraphs)


@dataclass
class _OpenElement:
    tag: str
    dropped: bool
    content_root: str | None


class _TextExtractor(HTMLParser):
    """Collects headings and paragraphs, skipping dropped elements and noting their container."""

    def __init__(self, drop_classes: frozenset[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.drop_classes = drop_classes
        self.blocks: list[tuple[Block, frozenset[str]]] = []
        self._stack: list[_OpenElement] = []
        self._buffer: list[str] = []
        self._heading_level = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BLOCK_TAGS or tag in HEADING_TAGS:
            self._flush()
        if tag in HEADING_TAGS and not self._skipping():
            self._heading_level = HEADING_TAGS[tag]
        if tag in CELL_TAGS and "".join(self._buffer).strip():
            self._buffer.append(CELL_SEPARATOR)
        if tag == "li" and not self._skipping():
            self._buffer.append(LIST_ITEM_PREFIX)
        if tag in VOID_TAGS:
            return
        classes = frozenset((dict(attrs).get("class") or "").split())
        dropped = tag in DROPPED_TAGS or bool(classes & self.drop_classes)
        root = tag if tag in ("article", "main") else None
        self._stack.append(_OpenElement(tag, dropped, root))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in BLOCK_TAGS or tag in HEADING_TAGS:
            self._flush()
        if tag in HEADING_TAGS:
            self._heading_level = 0
        if tag == "li":
            # An empty item leaves only its marker, which must not mark the next paragraph.
            self._buffer = []
        # Optional end tags (</p>, </li>) are often left out: close back to the matching element.
        if not any(element.tag == tag for element in self._stack):
            return
        while self._stack:
            if self._stack.pop().tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if not self._skipping():
            self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _skipping(self) -> bool:
        return any(element.dropped for element in self._stack)

    def _roots(self) -> frozenset[str]:
        return frozenset(e.content_root for e in self._stack if e.content_root is not None)

    def _flush(self) -> None:
        text = " ".join("".join(self._buffer).split())
        self._buffer = []
        if text == LIST_ITEM_PREFIX.strip():
            # A list item whose text sits in a nested paragraph keeps its marker for that text.
            self._buffer = [LIST_ITEM_PREFIX]
        elif text:
            self.blocks.append((Block(text, self._heading_level), self._roots()))


def extract_blocks(html: str, drop_classes: Iterable[str] = ()) -> list[Block]:
    """Return the readable headings and paragraphs of an HTML page, in document order.

    Scripts, styles, navigation, headers, footers and elements carrying one of `drop_classes`
    are left out. When the page has an <article>, only its text is kept; otherwise its <main>;
    otherwise the whole body. Whitespace is collapsed; character references are decoded.
    """
    extractor = _TextExtractor(drop_classes=ALWAYS_DROPPED_CLASSES | frozenset(drop_classes))
    extractor.feed(html)
    extractor.close()
    for root in ("article", "main"):
        inside = [block for block, roots in extractor.blocks if root in roots]
        if inside:
            return inside
    return [block for block, _ in extractor.blocks]


def markdown_blocks(markdown: str) -> list[Block]:
    """Return the headings and paragraphs of a project note written in plain Markdown.

    A line starting with one to six '#' is a heading; blank lines separate paragraphs, and a
    paragraph's lines are joined with single spaces, except list items, which stay one per line.
    """
    blocks: list[Block] = []
    lines: list[str] = []

    def flush() -> None:
        if lines:
            blocks.append(Block("\n".join(lines)))
            lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        heading = MARKDOWN_HEADING.match(line)
        if heading:
            flush()
            blocks.append(Block(heading.group(2), len(heading.group(1))))
        elif not line:
            flush()
        elif line.startswith(LIST_ITEM_PREFIX) or not lines:
            lines.append(line)
        else:
            lines[-1] = f"{lines[-1]} {line}"
    flush()
    return blocks


def split_sections(blocks: Iterable[Block], source_title: str) -> list[Section]:
    """Split blocks into sections at each heading, then bound their length.

    Text before the first heading forms a section titled `source_title`. Consecutive headings
    form one title ("Chapter: Subsection"); a heading with no text after it is left out. A
    section shorter than MIN_SECTION_CHARS joins the one before it, keeping its heading as a
    paragraph, or the one after it when the one before is missing or would grow past
    MAX_SECTION_CHARS. A section longer than MAX_SECTION_CHARS splits into parts of about equal
    length at paragraph boundaries, and a single over-long paragraph at sentence ends.
    """
    raw = _sections_by_heading(blocks, source_title)
    merged = _merge_short(raw)
    return [part for section in merged for part in _split_long(section)]


def _sections_by_heading(blocks: Iterable[Block], source_title: str) -> list[Section]:
    sections: list[Section] = []
    title: str | None = None
    paragraphs: list[str] = []
    for block in blocks:
        if block.level == 0:
            paragraphs.append(block.text)
        elif title is not None and not paragraphs:
            # A heading straight after another, such as a chapter and its first subsection.
            title = title if block.text == title else f"{title}: {block.text}"
        else:
            if paragraphs:
                sections.append(Section(title or source_title, tuple(paragraphs)))
            title, paragraphs = block.text, []
    # A heading with no text after it, such as a closing "Related links", is left out.
    if paragraphs:
        sections.append(Section(title or source_title, tuple(paragraphs)))
    return sections


def _merge_short(sections: list[Section]) -> list[Section]:
    merged: list[Section] = []
    waiting: Section | None = None  # a short section that joins the one after it
    for section in sections:
        if waiting is not None:
            section, waiting = _joined(waiting, section), None
        if len(section.body) >= MIN_SECTION_CHARS:
            merged.append(section)
        elif merged and len(merged[-1].body) + len(section.body) <= MAX_SECTION_CHARS:
            merged[-1] = _joined(merged[-1], section)
        else:
            waiting = section
    if waiting is not None:
        merged.append(_joined(merged.pop(), waiting) if merged else waiting)
    return merged


def _joined(first: Section, second: Section) -> Section:
    """Return `second` appended to `first`, its heading kept as a paragraph."""
    return Section(first.title, (*first.paragraphs, second.title, *second.paragraphs))


def _split_long(section: Section) -> list[Section]:
    if len(section.body) <= MAX_SECTION_CHARS:
        return [section]
    pieces = [piece for paragraph in section.paragraphs for piece in _bounded_pieces(paragraph)]
    # Aim for parts of equal length, so the last part is not a short leftover.
    target = len(section.body) / math.ceil(len(section.body) / MAX_SECTION_CHARS)
    parts: list[list[str]] = [[]]
    for piece in pieces:
        if parts[-1] and len("\n\n".join([*parts[-1], piece])) > MAX_SECTION_CHARS:
            parts.append([])
        parts[-1].append(piece)
        if len("\n\n".join(parts[-1])) >= target:
            parts.append([])
    parts = [part for part in parts if part]
    return [
        Section(section.title if index == 0 else f"{section.title} (part {index + 1})", tuple(part))
        for index, part in enumerate(parts)
    ]


def _bounded_pieces(paragraph: str) -> list[str]:
    """Return the paragraph whole, or cut at sentence ends into pieces of at most the maximum."""
    if len(paragraph) <= MAX_SECTION_CHARS:
        return [paragraph]
    pieces: list[str] = [""]
    for sentence in SENTENCE_END.split(paragraph):
        candidate = f"{pieces[-1]} {sentence}".strip()
        if pieces[-1] and len(candidate) > MAX_SECTION_CHARS:
            pieces.append(sentence)
        else:
            pieces[-1] = candidate
    return pieces


def section_text(source: dict[str, Any], section: Section) -> str:
    """Return a section file's content: lines naming the source and publisher, then the text."""
    heading = source["title"]
    if section.title != heading:
        heading = f"{heading}: {section.title}"
    return f"{heading}\nPublisher: {source['publisher']}\n\n{section.body}\n"


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of `data`."""
    return hashlib.sha256(data).hexdigest()


def corpus_version(manifest: dict[str, Any]) -> str:
    """Return the SHA-256 of the manifest's canonical JSON, leaving out `corpus_version` itself.

    Canonical means sorted keys, no insignificant whitespace and UTF-8, so the same sources,
    sections and access dates always give the same version.
    """
    content = {key: value for key, value in manifest.items() if key != "corpus_version"}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_hex(canonical.encode("utf-8"))


def urllib_fetch(url: str) -> Response:
    """Download `url` with the generic user agent and a timeout, following redirects.

    An HTTP error status is returned as a Response; a network failure raises FetchError.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as reply:
            return Response(reply.status, reply.headers.get_content_type(), reply.read())
    except urllib.error.HTTPError as error:
        return Response(error.code, error.headers.get_content_type(), error.read())
    except (OSError, http.client.HTTPException) as error:
        raise FetchError(f"{url}: {error}") from error


def robots_allows(url: str, fetch: Fetcher) -> bool:
    """Return whether the site's robots.txt lets USER_AGENT fetch `url`.

    RFC 9309, 2.3.1: a robots.txt that is unavailable (4xx), or a 200 that is not plain text
    (for example a redirect to an HTML page), sets no rules, so everything is allowed. Any
    other status, such as a 5xx, means the rules are unreachable: raises FetchError, so the
    build stops instead of fetching pages whose rules it could not read.
    """
    parts = urlsplit(url)
    reply = fetch(f"{parts.scheme}://{parts.netloc}/robots.txt")
    if HTTP_CLIENT_ERROR_MIN <= reply.status <= HTTP_CLIENT_ERROR_MAX:
        return True
    if reply.status != HTTP_OK:
        raise FetchError(f"{url}: robots.txt is unreachable (HTTP {reply.status})")
    if reply.content_type != "text/plain":
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(reply.body.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(USER_AGENT, url)


def fetch_page(url: str, fetch: Fetcher) -> bytes:
    """Return the HTML body of `url`, or raise FetchError when robots.txt, status or type forbid."""
    if not robots_allows(url, fetch):
        raise FetchError(f"{url}: robots.txt disallows this user agent")
    reply = fetch(url)
    if reply.status != HTTP_OK:
        raise FetchError(f"{url}: HTTP {reply.status}")
    if reply.content_type != "text/html":
        raise FetchError(f"{url}: expected text/html, got {reply.content_type}")
    return reply.body


def source_sections(source: dict[str, Any], content: bytes) -> list[Section]:
    """Return the sections of a source's raw content: HTML for agency pages, else Markdown."""
    text = content.decode("utf-8", errors="replace")
    if source["kind"] == KIND_PROJECT:
        blocks = markdown_blocks(text)
    else:
        blocks = extract_blocks(text, source.get("drop_classes", ()))
    return split_sections(blocks, source["title"])


def load_content(source: dict[str, Any], corpus_dir: Path, raw_dir: Path, fetch: Fetcher) -> bytes:
    """Return a source's raw content: a project note read from disk, or a page downloaded and
    saved under `raw_dir` as `{source_id}.html`."""
    if source["kind"] == KIND_PROJECT:
        return (corpus_dir / source["path"]).read_bytes()
    content = fetch_page(source["url"], fetch)
    (raw_dir / f"{source['source_id']}.html").write_bytes(content)
    return content


def build_corpus(
    sources: list[dict[str, Any]],
    corpus_dir: Path,
    raw_dir: Path,
    accessed: date,
    fetch: Fetcher,
    delay_seconds: float = 0.0,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Return the manifest and the section files (name -> text) for the reviewed sources.

    Each source keeps its reviewed metadata plus the access date and the SHA-256 of its raw
    content; each section records its ID, title, source, length in characters and SHA-256.
    Raises FetchError when any agency page cannot be fetched; nothing is written here.
    """
    manifest_sources: list[dict[str, Any]] = []
    manifest_sections: list[dict[str, Any]] = []
    files: dict[str, str] = {}
    for index, source in enumerate(sources):
        if index and source["kind"] != KIND_PROJECT:
            time.sleep(delay_seconds)
        content = load_content(source, corpus_dir, raw_dir, fetch)
        manifest_sources.append(_manifest_source(source, content, accessed))
        for number, section in enumerate(source_sections(source, content), start=1):
            section_id = f"{source['source_id']}-{number:02d}"
            text = section_text(source, section)
            files[f"{section_id}.txt"] = text
            manifest_sections.append(_manifest_section(section_id, source, section, text))
    manifest: dict[str, Any] = {"sources": manifest_sources, "sections": manifest_sections}
    manifest["corpus_version"] = corpus_version(manifest)
    return manifest, files


def _manifest_source(source: dict[str, Any], content: bytes, accessed: date) -> dict[str, Any]:
    return {
        "source_id": source["source_id"],
        "kind": source["kind"],
        "publisher": source["publisher"],
        "title": source["title"],
        "url": source["url"],
        "version": source.get("version"),
        "accessed": accessed.isoformat(),
        "sha256": sha256_hex(content),
    }


def _manifest_section(
    section_id: str, source: dict[str, Any], section: Section, text: str
) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "source_id": source["source_id"],
        "title": section.title,
        "path": f"{SECTIONS_DIR}/{section_id}.txt",
        "chars": len(text),
        "sha256": sha256_hex(text.encode("utf-8")),
    }


def write_corpus(corpus_dir: Path, manifest: dict[str, Any], files: dict[str, str]) -> None:
    """Write the manifest and section files, removing section files the manifest no longer has."""
    sections_dir = corpus_dir / SECTIONS_DIR
    sections_dir.mkdir(parents=True, exist_ok=True)
    for stale in sections_dir.glob("*.txt"):
        if stale.name not in files:
            stale.unlink()
    for name, text in files.items():
        (sections_dir / name).write_text(text, encoding="utf-8")
    document = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (corpus_dir / MANIFEST_FILE).write_text(document, encoding="utf-8")


def _empty_directory(value: str) -> Path:
    path = Path(value)
    if path.exists() and any(path.iterdir()):
        raise argparse.ArgumentTypeError(f"{path} is not empty")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--accessed", type=date.fromisoformat, required=True)
    parser.add_argument("--raw-dir", type=_empty_directory, required=True)
    arguments = parser.parse_args()
    arguments.raw_dir.mkdir(parents=True, exist_ok=True)
    sources = json.loads((CORPUS_DIR / SOURCES_FILE).read_text(encoding="utf-8"))["sources"]
    try:
        manifest, files = build_corpus(
            sources,
            CORPUS_DIR,
            arguments.raw_dir,
            arguments.accessed,
            urllib_fetch,
            DELAY_BETWEEN_FETCHES_SECONDS,
        )
    except FetchError as error:
        print(f"Build stopped, nothing written: {error}", file=sys.stderr)
        return 1
    write_corpus(CORPUS_DIR, manifest, files)
    print(
        f"{len(manifest['sources'])} sources, {len(manifest['sections'])} sections, "
        f"corpus_version {manifest['corpus_version']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
