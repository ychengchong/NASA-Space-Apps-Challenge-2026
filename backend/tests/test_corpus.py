"""Tests for the corpus build script (spec 8, "Planned corpus and retrieval"). No network."""

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from app.catalogue import load_catalogue
from scripts.build_corpus import (
    CORPUS_DIR,
    MANIFEST_FILE,
    MAX_SECTION_CHARS,
    MIN_SECTION_CHARS,
    SOURCES_FILE,
    Block,
    FetchError,
    Response,
    build_corpus,
    corpus_version,
    extract_blocks,
    markdown_blocks,
    split_sections,
    write_corpus,
)

ACCESSED = date(2026, 11, 15)
LONG_TEXT = "Monthly values are averaged from daily values. " * 6
PAGE = f"""<!doctype html><html><head><title>t</title><style>.a {{ color: red }}</style>
<script>var tracking = "do not keep";</script></head><body>
<header><a href="/">Site header</a></header>
<nav><ul><li>Home<li>Docs</ul></nav>
<article>
<h1>Processing<a class="headerlink" href="#p">&para;</a></h1>
<p>{LONG_TEXT}</p>
<h2>Hierarchy</h2>
<p>Annual values are means of monthly values &amp; never sums. {LONG_TEXT}</p>
</article>
<footer>Footer text</footer>
</body></html>"""
ROBOTS_ALLOW = b"User-agent: *\nDisallow: /private/\n"


def _fetcher(pages: dict[str, Response]) -> Any:
    def fetch(url: str) -> Response:
        if url in pages:
            return pages[url]
        if url.endswith("/robots.txt"):
            return Response(404, "text/html", b"not found")
        raise AssertionError(f"unexpected fetch of {url}")

    return fetch


def _html(body: str) -> Response:
    return Response(200, "text/html", body.encode("utf-8"))


def _agency(url: str = "https://power.example.gov/docs/processing/") -> dict[str, Any]:
    return {
        "source_id": "power-processing",
        "kind": "agency",
        "publisher": "NASA Langley Research Center, POWER Project",
        "title": "POWER Data Processing",
        "url": url,
    }


def _project(corpus_dir: Path) -> dict[str, Any]:
    (corpus_dir / "project").mkdir(parents=True, exist_ok=True)
    note = (
        f"# Sen's slope\n\nThe median of pairwise rates.\n{LONG_TEXT}\n\n## Zero\n\n{LONG_TEXT}\n"
    )
    (corpus_dir / "project" / "sen.md").write_text(note, encoding="utf-8")
    return {
        "source_id": "project-sen-slope",
        "kind": "project",
        "publisher": "Trend Detective project",
        "title": "Sen's slope",
        "url": "https://example.org/sen.md",
        "path": "project/sen.md",
    }


def _build(tmp_path: Path, sources: list[dict[str, Any]], page: str = PAGE) -> Any:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    fetch = _fetcher({"https://power.example.gov/docs/processing/": _html(page)})
    return build_corpus(sources, tmp_path, raw_dir, ACCESSED, fetch)


def test_extraction_drops_scripts_styles_navigation_header_and_footer() -> None:
    text = " ".join(block.text for block in extract_blocks(PAGE))

    for furniture in ("do not keep", "color", "Site header", "Home", "Docs", "Footer text"):
        assert furniture not in text


def test_extraction_keeps_headings_and_decodes_character_references() -> None:
    blocks = extract_blocks(PAGE)

    assert [block.text for block in blocks if block.level] == ["Processing", "Hierarchy"]
    assert blocks[0].level == 1
    assert "means of monthly values & never sums." in blocks[3].text


def test_extraction_drops_heading_permalinks() -> None:
    assert "¶" not in " ".join(block.text for block in extract_blocks(PAGE))


def test_extraction_keeps_only_the_article_when_the_page_has_one() -> None:
    page = "<body><div><p>Outside text</p></div><article><p>Inside text</p></article></body>"

    assert extract_blocks(page) == [Block("Inside text")]


def test_extraction_uses_main_when_there_is_no_article() -> None:
    page = "<body><p>Banner</p><main><p>Main text</p></main></body>"

    assert extract_blocks(page) == [Block("Main text")]


def test_extraction_drops_elements_with_a_listed_class() -> None:
    page = '<main><div class="menu side"><p>Menu link</p></div><p>Body</p></main>'

    assert extract_blocks(page, ["side"]) == [Block("Body")]


def test_extraction_closes_list_items_whose_end_tags_are_left_out() -> None:
    page = "<main><nav><ul><li>One<li>Two</ul></nav><ul><li>Kept<li>Also kept</ul></main>"

    assert extract_blocks(page) == [Block("- Kept"), Block("- Also kept")]


def test_extraction_keeps_the_marker_of_a_list_item_with_a_nested_paragraph() -> None:
    page = "<main><ul><li><p>Nested</p></li><li></li></ul><p>After</p></main>"

    assert extract_blocks(page) == [Block("- Nested"), Block("After")]


def test_extraction_joins_table_cells_of_a_row() -> None:
    page = "<main><table><tr> <th>Hourly</th> <th>Daily</th> </tr></table></main>"

    assert extract_blocks(page) == [Block("Hourly | Daily")]


def test_markdown_note_gives_headings_and_paragraphs() -> None:
    note = "# Title\n\nFirst line\nsecond line.\n\n- item one\n- item two\n\n## Next\n\nText."

    assert markdown_blocks(note) == [
        Block("Title", 1),
        Block("First line second line."),
        Block("- item one\n- item two"),
        Block("Next", 2),
        Block("Text."),
    ]


def test_each_heading_starts_a_section() -> None:
    blocks = [Block("A", 1), Block(LONG_TEXT), Block("B", 2), Block(LONG_TEXT)]

    sections = split_sections(blocks, "Page")

    assert [section.title for section in sections] == ["A", "B"]
    assert sections[1].paragraphs == (LONG_TEXT,)


def test_text_before_the_first_heading_is_titled_with_the_source_title() -> None:
    sections = split_sections([Block(LONG_TEXT), Block("A", 2), Block(LONG_TEXT)], "Page")

    assert [section.title for section in sections] == ["Page", "A"]


def test_consecutive_headings_form_one_title() -> None:
    sections = split_sections([Block("Chapter", 1), Block("Part", 2), Block(LONG_TEXT)], "Page")

    assert [section.title for section in sections] == ["Chapter: Part"]


def test_a_heading_without_text_after_it_is_left_out() -> None:
    sections = split_sections([Block("A", 1), Block(LONG_TEXT), Block("Related", 5)], "Page")

    assert [section.title for section in sections] == ["A"]
    assert "Related" not in sections[0].body


def test_a_short_section_joins_the_one_before_it() -> None:
    blocks = [Block("A", 1), Block(LONG_TEXT), Block("Short", 2), Block("Tiny text.")]

    sections = split_sections(blocks, "Page")

    assert len(sections) == 1
    assert sections[0].paragraphs == (LONG_TEXT, "Short", "Tiny text.")


def test_a_short_first_section_joins_the_one_after_it() -> None:
    blocks = [Block("Intro", 1), Block("Tiny."), Block("B", 2), Block(LONG_TEXT)]

    sections = split_sections(blocks, "Page")

    assert [section.title for section in sections] == ["Intro"]
    assert sections[0].paragraphs == ("Tiny.", "B", LONG_TEXT)


def test_a_long_section_splits_at_paragraph_boundaries_into_even_parts() -> None:
    paragraph = "word " * 150 + "end."
    blocks = [Block("Long", 1), *(Block(paragraph) for _ in range(8))]

    sections = split_sections(blocks, "Page")

    assert [section.title for section in sections] == ["Long", "Long (part 2)", "Long (part 3)"]
    assert all(MIN_SECTION_CHARS <= len(s.body) <= MAX_SECTION_CHARS for s in sections)
    assert all(set(section.paragraphs) == {paragraph} for section in sections)


def test_an_over_long_paragraph_splits_at_sentence_ends() -> None:
    sentence = (
        "This sentence is about one hundred characters long, written to fill a test paragraph. "
    )
    paragraph = (sentence * 40).strip()

    sections = split_sections([Block("Long", 1), Block(paragraph)], "Page")

    assert len(sections) == 2
    assert all(len(section.body) <= MAX_SECTION_CHARS for section in sections)
    assert all(section.body.endswith("paragraph.") for section in sections)


def test_corpus_version_is_the_hash_of_the_manifest_without_its_own_field() -> None:
    manifest = {"sources": [{"source_id": "a"}], "sections": []}
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")

    with_version = {**manifest, "corpus_version": "anything"}

    assert corpus_version(with_version) == hashlib.sha256(canonical).hexdigest()


def test_corpus_version_changes_when_a_section_changes() -> None:
    first = {"sections": [{"sha256": "aa"}], "sources": []}
    second = {"sections": [{"sha256": "bb"}], "sources": []}

    assert corpus_version(first) != corpus_version(second)


def test_build_records_source_and_section_hashes(tmp_path: Path) -> None:
    manifest, files = _build(tmp_path, [_agency()])

    source = manifest["sources"][0]
    assert source["sha256"] == hashlib.sha256(PAGE.encode("utf-8")).hexdigest()
    assert source["accessed"] == "2026-11-15"
    assert [s["section_id"] for s in manifest["sections"]] == [
        "power-processing-01",
        "power-processing-02",
    ]
    for section in manifest["sections"]:
        text = files[Path(section["path"]).name]
        assert section["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert section["chars"] == len(text)
    assert manifest["corpus_version"] == corpus_version(manifest)


def test_section_file_names_its_source_and_publisher(tmp_path: Path) -> None:
    _, files = _build(tmp_path, [_agency()])

    text = files["power-processing-02.txt"]
    assert text.startswith("POWER Data Processing: Hierarchy\n")
    assert "Publisher: NASA Langley Research Center, POWER Project\n" in text


def test_section_file_does_not_repeat_a_title_equal_to_the_source_title(tmp_path: Path) -> None:
    _, files = _build(tmp_path, [_agency() | {"title": "Processing"}])

    assert files["power-processing-01.txt"].startswith("Processing\nPublisher: ")


def test_build_saves_the_raw_page_in_the_raw_directory(tmp_path: Path) -> None:
    _build(tmp_path, [_agency()])

    assert (tmp_path / "raw" / "power-processing.html").read_text(encoding="utf-8") == PAGE


def test_build_includes_project_notes_with_kind_project(tmp_path: Path) -> None:
    project = _project(tmp_path)

    manifest, files = _build(tmp_path, [_agency(), project])

    note = manifest["sources"][1]
    assert note["kind"] == "project"
    assert note["publisher"] == "Trend Detective project"
    project_sections = [s for s in manifest["sections"] if s["source_id"] == "project-sen-slope"]
    assert [s["title"] for s in project_sections] == ["Sen's slope", "Zero"]
    assert "Publisher: Trend Detective project" in files["project-sen-slope-01.txt"]


def test_the_same_inputs_give_the_same_corpus_version(tmp_path: Path) -> None:
    first, _ = _build(tmp_path, [_agency()])
    second, _ = _build(tmp_path, [_agency()])

    assert first["corpus_version"] == second["corpus_version"]


def test_changed_page_text_changes_the_corpus_version(tmp_path: Path) -> None:
    first, _ = _build(tmp_path, [_agency()])
    second, _ = _build(tmp_path, [_agency()], PAGE.replace("never sums", "not sums"))

    assert first["corpus_version"] != second["corpus_version"]


def test_a_failed_download_stops_the_build(tmp_path: Path) -> None:
    fetch = _fetcher(
        {"https://power.example.gov/docs/processing/": Response(404, "text/html", b"")}
    )

    with pytest.raises(FetchError, match="HTTP 404"):
        build_corpus([_agency()], tmp_path, tmp_path, ACCESSED, fetch)


def test_a_page_that_is_not_html_stops_the_build(tmp_path: Path) -> None:
    pdf = Response(200, "application/pdf", b"%PDF")
    fetch = _fetcher({"https://power.example.gov/docs/processing/": pdf})

    with pytest.raises(FetchError, match="expected text/html"):
        build_corpus([_agency()], tmp_path, tmp_path, ACCESSED, fetch)


def test_robots_txt_that_disallows_the_page_stops_the_build(tmp_path: Path) -> None:
    robots = Response(200, "text/plain", b"User-agent: *\nDisallow: /docs/\n")
    fetch = _fetcher({"https://power.example.gov/robots.txt": robots})

    with pytest.raises(FetchError, match=r"robots\.txt"):
        build_corpus([_agency()], tmp_path, tmp_path, ACCESSED, fetch)


def test_robots_txt_server_error_stops_the_build(tmp_path: Path) -> None:
    unreachable = Response(503, "text/html", b"unavailable")
    fetch = _fetcher({"https://power.example.gov/robots.txt": unreachable})

    with pytest.raises(FetchError, match=r"robots\.txt is unreachable \(HTTP 503\)"):
        build_corpus([_agency()], tmp_path, tmp_path, ACCESSED, fetch)


def test_missing_robots_txt_sets_no_rules(tmp_path: Path) -> None:
    fetch = _fetcher(
        {
            "https://power.example.gov/robots.txt": Response(404, "text/html", b"not found"),
            "https://power.example.gov/docs/processing/": _html(PAGE),
        }
    )

    manifest, _ = build_corpus([_agency()], tmp_path, tmp_path, ACCESSED, fetch)

    assert len(manifest["sections"]) == 2


def test_robots_txt_that_allows_the_page_lets_the_build_run(tmp_path: Path) -> None:
    fetch = _fetcher(
        {
            "https://power.example.gov/robots.txt": Response(200, "text/plain", ROBOTS_ALLOW),
            "https://power.example.gov/docs/processing/": _html(PAGE),
        }
    )

    manifest, _ = build_corpus([_agency()], tmp_path, tmp_path, ACCESSED, fetch)

    assert len(manifest["sections"]) == 2


def test_written_section_bytes_match_the_manifest_on_every_platform(tmp_path: Path) -> None:
    manifest, files = _build(tmp_path, [_agency()])

    write_corpus(tmp_path / "corpus", manifest, files)

    for section in manifest["sections"]:
        content = (tmp_path / "corpus" / section["path"]).read_bytes()
        assert b"\r\n" not in content
        assert hashlib.sha256(content).hexdigest() == section["sha256"]


def test_write_corpus_removes_section_files_the_manifest_no_longer_lists(tmp_path: Path) -> None:
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    (sections_dir / "old-01.txt").write_text("stale", encoding="utf-8")
    manifest, files = _build(tmp_path, [_agency()])

    write_corpus(tmp_path, manifest, files)

    assert sorted(path.name for path in sections_dir.iterdir()) == sorted(files)
    written = json.loads((tmp_path / MANIFEST_FILE).read_text(encoding="utf-8"))
    assert written == manifest


def test_reviewed_sources_are_nasa_pages_or_existing_project_notes() -> None:
    sources = json.loads((CORPUS_DIR / SOURCES_FILE).read_text(encoding="utf-8"))["sources"]

    assert len({source["source_id"] for source in sources}) == len(sources)
    for source in sources:
        if source["kind"] == "agency":
            assert urlsplit(source["url"]).hostname.endswith(".nasa.gov")
        else:
            assert source["kind"] == "project"
            assert source["publisher"] == "Trend Detective project"
            assert (CORPUS_DIR / source["path"]).is_file()


def test_committed_manifest_matches_its_section_files() -> None:
    manifest = json.loads((CORPUS_DIR / MANIFEST_FILE).read_text(encoding="utf-8"))

    assert manifest["corpus_version"] == corpus_version(manifest)
    for section in manifest["sections"]:
        content = (CORPUS_DIR / section["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == section["sha256"]
    listed = {Path(section["path"]).name for section in manifest["sections"]}
    assert {path.name for path in (CORPUS_DIR / "sections").iterdir()} == listed


def test_variables_note_copies_every_catalogue_variable() -> None:
    note = (CORPUS_DIR / "project" / "variables.md").read_text(encoding="utf-8")

    for entry in load_catalogue():
        assert f"## {entry.name} ({entry.code})" in note
        assert f"{entry.name} ({entry.code}): {entry.definition}" in note
        assert f"- Catalogue ID: {entry.id}" in note
        assert f"- Units: {entry.units}" in note
        if entry.trend_note:
            assert f"Caution: {entry.trend_note}" in note
