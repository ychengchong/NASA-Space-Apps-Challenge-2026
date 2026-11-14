"""The reviewed corpus manifest, read once (spec 8, "Planned corpus and retrieval").

Discovery and explanation cite only passages that were retrieved for the request, whose
section the manifest lists, and whose text is part of that section's reviewed file. Every
citation field comes from the manifest or the retrieved text, never from model text.
"""

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app import ai
from app.ai_guard import Evidence
from app.config import CORPUS_MANIFEST_PATH
from app.models import MAX_PASSAGES, Citation, DocumentSource, RetrievedPassage


class CorpusError(ValueError):
    """The manifest is missing, unreadable or malformed, so nothing can be cited."""


@dataclass(frozen=True)
class Corpus:
    """The manifest's version, its sections keyed by section ID, and each section's reviewed
    text with its whitespace collapsed, also keyed by section ID.
    """

    version: str
    sections: Mapping[str, DocumentSource]
    texts: Mapping[str, str]

    def document(self, source_id: str, section_id: str) -> DocumentSource | None:
        """The manifest section `section_id` of source `source_id`; None when the manifest has
        no such section or the section belongs to another source.
        """
        document = self.sections.get(section_id)
        if document is None or document.source_id != source_id:
            return None
        return document

    def has_source(self, source_id: str) -> bool:
        return any(document.source_id == source_id for document in self.sections.values())

    def citable(self, passages: Iterable[RetrievedPassage]) -> list[RetrievedPassage]:
        """The passages, in order, whose source and section the manifest lists and whose text
        is part of that section's reviewed file, ignoring differences in whitespace.

        A hit from a file the manifest does not describe, or one carrying a section's
        attributes with other text (a stale or foreign file in the vector store), cannot be
        cited, so it is never shown to the model either.
        """
        return [
            passage
            for passage in passages
            if self.document(passage.source_id, passage.section_id) is not None
            and _collapse(passage.text) in self.texts[passage.section_id]
        ]

    def citation(self, passage: RetrievedPassage) -> Citation:
        """The server-built citation of a retrieved passage. Raises `CorpusError` when the
        manifest does not list the passage's section.
        """
        document = self.document(passage.source_id, passage.section_id)
        if document is None:
            raise CorpusError("The manifest does not list this passage's section.")
        return ai.citation(passage, document)

    def evidence(self, passages: Sequence[RetrievedPassage]) -> Evidence:
        """The retrieved passages and the manifest's IDs, for the citation checks."""
        return Evidence(
            passages=passages,
            known_source_ids=frozenset(doc.source_id for doc in self.sections.values()),
            known_section_ids=frozenset(self.sections),
        )

    def citations(self, source_ids: Iterable[str], evidence: Evidence) -> list[Citation]:
        """The server-built citations of the retrieved passages that `source_ids` name, in the
        order cited, each passage once, at most `MAX_PASSAGES`. The IDs must already have
        passed `ai_guard.check_citations`.
        """
        cited: list[RetrievedPassage] = []
        for source_id in source_ids:
            cited += [passage for passage in evidence.cited(source_id) if passage not in cited]
        return [self.citation(passage) for passage in cited[:MAX_PASSAGES]]


def prompt_passages(passages: Iterable[RetrievedPassage], corpus: Corpus) -> list[dict[str, str]]:
    """The passages as the provider sees them: the ID to cite, where each comes from, and its
    text. Only manifest fields and retrieved text are shown, never a URL.
    """
    shown: list[dict[str, str]] = []
    for passage in passages:
        document = corpus.document(passage.source_id, passage.section_id)
        if document is None:
            continue
        shown.append(
            {
                "id": passage.section_id,
                "publisher": document.publisher,
                "title": document.title,
                "section": document.section,
                "kind": document.kind,
                "text": passage.text,
            }
        )
    return shown


@lru_cache(maxsize=1)
def load_corpus(path: Path = CORPUS_MANIFEST_PATH) -> Corpus:
    """The manifest at `path`, read and checked once per path.

    Raises `CorpusError` for an unreadable file, invalid JSON, a missing version, a section of
    an unknown source, a source or section that does not fit `DocumentSource`, or a section
    file, read from the manifest's `path` beside it, that is missing or fails its SHA-256.
    """
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CorpusError("The corpus manifest cannot be read.") from error
    try:
        return _corpus(manifest, path.parent)
    except (KeyError, TypeError, AttributeError, ValidationError) as error:
        raise CorpusError("The corpus manifest is malformed.") from error


def _corpus(manifest: Mapping[str, object], directory: Path) -> Corpus:
    version = manifest["corpus_version"]
    if not isinstance(version, str) or version == "":
        raise CorpusError("The corpus manifest has no version.")
    sources = {source["source_id"]: source for source in _list(manifest["sources"])}
    sections: dict[str, DocumentSource] = {}
    texts: dict[str, str] = {}
    for section in _list(manifest["sections"]):
        source = sources.get(section["source_id"])
        if source is None:
            raise CorpusError("A manifest section names an unknown source.")
        sections[section["section_id"]] = DocumentSource(
            source_id=source["source_id"],
            section_id=section["section_id"],
            publisher=source["publisher"],
            title=source["title"],
            url=source["url"],
            section=section["title"],
            accessed=source["accessed"],
            version=source.get("version"),
            sha256=section["sha256"],
            kind=source["kind"],
        )
        texts[section["section_id"]] = _section_text(directory / section["path"], section["sha256"])
    return Corpus(version=version, sections=sections, texts=texts)


def _section_text(path: Path, sha256: str) -> str:
    """The reviewed text of one section file, whitespace collapsed, after its SHA-256 check."""
    try:
        content = path.read_bytes()
    except OSError as error:
        raise CorpusError("A corpus section file cannot be read.") from error
    if hashlib.sha256(content).hexdigest() != sha256:
        raise CorpusError("A corpus section file does not match the manifest.")
    try:
        return _collapse(content.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise CorpusError("A corpus section file is not UTF-8 text.") from error


def _collapse(text: str) -> str:
    """`text` with every run of whitespace as one space. A replacement character at either end,
    left where retrieval cut a multi-byte character, is dropped.
    """
    return " ".join(text.split()).strip("\ufffd ")


def _list(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CorpusError("The corpus manifest is malformed.")
    return value
