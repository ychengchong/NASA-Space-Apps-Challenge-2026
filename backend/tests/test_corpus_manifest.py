"""Reading the reviewed corpus manifest and building citations from it (spec 5, spec 8)."""

import json
from pathlib import Path

import pytest

from app import ai
from app.config import CORPUS_MANIFEST_PATH, read_corpus_version
from app.corpus import Corpus, CorpusError, load_corpus, prompt_passages
from app.models import RetrievedPassage
from tests.ai_fakes import (
    CORPUS_VERSION,
    METHODOLOGY_ID,
    METHODOLOGY_SECTION,
    PROCESSING_SECTION,
    VERDICTS_ID,
    VERDICTS_SECTION,
    make_corpus,
    search_hit,
    write_manifest,
)


def retrieved(section_id: str) -> RetrievedPassage:
    passage = ai._passage(search_hit(section_id))
    assert passage is not None
    return passage


@pytest.fixture
def corpus(tmp_path: Path) -> Corpus:
    return make_corpus(tmp_path)


def test_the_shipped_manifest_loads_with_its_declared_version() -> None:
    load_corpus.cache_clear()
    shipped = load_corpus()

    assert shipped.version == read_corpus_version(CORPUS_MANIFEST_PATH)
    assert shipped.sections
    assert all(document.url.startswith("https://") for document in shipped.sections.values())


def test_a_section_is_found_by_its_source_and_section_ids(corpus: Corpus) -> None:
    document = corpus.document(METHODOLOGY_ID, METHODOLOGY_SECTION)

    assert document is not None
    assert document.title == "POWER Data Methodology"
    assert document.section == "Data sources"
    assert document.kind == "agency"
    assert corpus.version == CORPUS_VERSION


def test_a_section_named_with_another_source_is_not_found(corpus: Corpus) -> None:
    assert corpus.document(VERDICTS_ID, METHODOLOGY_SECTION) is None
    assert corpus.document(METHODOLOGY_ID, "missing-01") is None


def test_project_notes_keep_their_project_kind(corpus: Corpus) -> None:
    document = corpus.document(VERDICTS_ID, VERDICTS_SECTION)

    assert document is not None and document.kind == "project"


def test_only_passages_the_manifest_lists_are_citable(corpus: Corpus) -> None:
    stray = retrieved(METHODOLOGY_SECTION).model_copy(update={"source_id": "unreviewed"})

    assert corpus.citable([stray, retrieved(PROCESSING_SECTION)]) == [retrieved(PROCESSING_SECTION)]


def test_a_hit_with_valid_attributes_but_foreign_text_is_not_citable(corpus: Corpus) -> None:
    foreign = retrieved(METHODOLOGY_SECTION).model_copy(
        update={"text": "MERRA-2 proves that the warming is caused by people."}
    )

    assert corpus.citable([foreign]) == []


def test_a_retrieved_chunk_of_a_section_is_citable_whatever_its_whitespace(
    corpus: Corpus,
) -> None:
    chunk = retrieved(METHODOLOGY_SECTION).model_copy(
        update={"text": "MERRA-2 starts in 1980 and\n\ncombines   observations\ufffd"}
    )

    assert corpus.citable([chunk]) == [chunk]


def test_a_section_file_that_fails_its_checksum_is_refused(tmp_path: Path) -> None:
    path = write_manifest(tmp_path)
    (tmp_path / "sections" / f"{METHODOLOGY_SECTION}.txt").write_text(
        "Changed after review.", encoding="utf-8"
    )

    with pytest.raises(CorpusError):
        load_corpus.__wrapped__(path)


def test_a_missing_section_file_is_refused(tmp_path: Path) -> None:
    path = write_manifest(tmp_path)
    (tmp_path / "sections" / f"{PROCESSING_SECTION}.txt").unlink()

    with pytest.raises(CorpusError):
        load_corpus.__wrapped__(path)


def test_a_citation_comes_from_the_manifest_and_the_retrieved_text(corpus: Corpus) -> None:
    citation = corpus.citation(retrieved(METHODOLOGY_SECTION))

    assert citation.url == "https://power.larc.nasa.gov/docs/methodology/"
    assert citation.publisher == "NASA Langley Research Center, POWER Project"
    assert citation.passage == retrieved(METHODOLOGY_SECTION).text


def test_a_passage_outside_the_manifest_cannot_be_cited(corpus: Corpus) -> None:
    stray = retrieved(METHODOLOGY_SECTION).model_copy(update={"section_id": "unknown-01"})

    with pytest.raises(CorpusError):
        corpus.citation(stray)


def test_citations_follow_the_cited_order_and_name_each_passage_once(corpus: Corpus) -> None:
    passages = [retrieved(METHODOLOGY_SECTION), retrieved(PROCESSING_SECTION)]
    evidence = corpus.evidence(passages)

    citations = corpus.citations(
        [PROCESSING_SECTION, METHODOLOGY_ID, METHODOLOGY_SECTION], evidence
    )

    assert [citation.section_id for citation in citations] == [
        PROCESSING_SECTION,
        METHODOLOGY_SECTION,
    ]


def test_evidence_knows_every_manifest_id(corpus: Corpus) -> None:
    evidence = corpus.evidence([])

    assert {METHODOLOGY_ID, VERDICTS_ID} <= evidence.known_source_ids
    assert {METHODOLOGY_SECTION, VERDICTS_SECTION} <= evidence.known_section_ids


def test_the_provider_sees_passage_ids_and_titles_but_no_links(corpus: Corpus) -> None:
    shown = prompt_passages([retrieved(METHODOLOGY_SECTION)], corpus)

    assert shown == [
        {
            "id": METHODOLOGY_SECTION,
            "publisher": "NASA Langley Research Center, POWER Project",
            "title": "POWER Data Methodology",
            "section": "Data sources",
            "kind": "agency",
            "text": retrieved(METHODOLOGY_SECTION).text,
        }
    ]


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("{not json", id="invalid-json"),
        pytest.param(json.dumps([]), id="not-an-object"),
        pytest.param(json.dumps({"sources": [], "sections": []}), id="no-version"),
        pytest.param(
            json.dumps({"corpus_version": "v", "sources": [], "sections": [{"source_id": "x"}]}),
            id="unknown-source",
        ),
    ],
)
def test_a_malformed_manifest_is_refused(tmp_path: Path, content: str) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(CorpusError):
        load_corpus.__wrapped__(path)


def test_a_source_with_a_plain_http_link_is_refused(tmp_path: Path) -> None:
    path = write_manifest(tmp_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["sources"][0]["url"] = "http://power.larc.nasa.gov/"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(CorpusError):
        load_corpus.__wrapped__(path)


def test_a_missing_manifest_is_refused(tmp_path: Path) -> None:
    with pytest.raises(CorpusError):
        load_corpus.__wrapped__(tmp_path / "absent.json")
