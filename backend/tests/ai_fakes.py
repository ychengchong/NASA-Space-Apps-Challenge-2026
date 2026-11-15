"""A fake OpenAI for the discovery and explanation tests: a vector store and a Responses API
served through httpx.MockTransport, so no test touches the network.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

import httpx
import pytest

from app import ai
from app.corpus import Corpus, load_corpus
from app.services import Services

STORE_ID = "vs_test123"
CORPUS_VERSION = "test-corpus-version"
SEARCH_PRICE = 2500
ACCESSED = date(2026, 11, 15)

METHODOLOGY_ID = "power-methodology"
METHODOLOGY_SECTION = "power-methodology-01"
METHODOLOGY_TEXT = (
    "POWER provides meteorology such as air temperature and WS10M wind from the MERRA-2 "
    "reanalysis. MERRA-2 starts in 1980 and combines observations with a weather model on a "
    "regular grid."
)
PROCESSING_SECTION = "power-methodology-02"
PROCESSING_TEXT = "Monthly air temperature values are averages of daily values over each month."
VERDICTS_ID = "project-verdicts"
VERDICTS_SECTION = "project-verdicts-01"
VERDICTS_TEXT = (
    "A result that is not significant means the evidence is insufficient; it does not mean "
    "that nothing changed."
)
# A section the manifest lists but the fake store never returns.
UNRETRIEVED_SECTION = "power-methodology-03"

SECTIONS = {
    METHODOLOGY_SECTION: (METHODOLOGY_ID, "Data sources", METHODOLOGY_TEXT),
    PROCESSING_SECTION: (METHODOLOGY_ID, "Processing", PROCESSING_TEXT),
    UNRETRIEVED_SECTION: (METHODOLOGY_ID, "Release history", "Release notes."),
    VERDICTS_SECTION: (VERDICTS_ID, "Verdict meanings", VERDICTS_TEXT),
}


def write_manifest(directory: Path) -> Path:
    """A small reviewed manifest with one agency source and one project source, and its
    section files.
    """
    (directory / "sections").mkdir(exist_ok=True)
    for section_id, (_, _, text) in SECTIONS.items():
        (directory / "sections" / f"{section_id}.txt").write_text(text, encoding="utf-8")
    manifest = {
        "corpus_version": CORPUS_VERSION,
        "sources": [
            {
                "source_id": METHODOLOGY_ID,
                "kind": "agency",
                "publisher": "NASA Langley Research Center, POWER Project",
                "title": "POWER Data Methodology",
                "url": "https://power.larc.nasa.gov/docs/methodology/",
                "version": None,
                "accessed": ACCESSED.isoformat(),
                "sha256": "a" * 64,
            },
            {
                "source_id": VERDICTS_ID,
                "kind": "project",
                "publisher": "Trend Detective project",
                "title": "What the verdicts mean",
                "url": "https://trend.example/docs/verdicts",
                "version": None,
                "accessed": ACCESSED.isoformat(),
                "sha256": "b" * 64,
            },
        ],
        "sections": [
            {
                "section_id": section_id,
                "source_id": source_id,
                "title": title,
                "path": f"sections/{section_id}.txt",
                "chars": len(text),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
            for section_id, (source_id, title, text) in SECTIONS.items()
        ],
    }
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def make_corpus(directory: Path) -> Corpus:
    load_corpus.cache_clear()
    corpus = load_corpus(write_manifest(directory))
    load_corpus.cache_clear()
    return corpus


def reviewed_as(corpus: Corpus, section_id: str, text: str) -> Corpus:
    """`corpus` as if the reviewed file of `section_id` held `text`, such as an injection that
    passed review, so the checks after retrieval can be tested on it.
    """
    return replace(corpus, texts={**corpus.texts, section_id: " ".join(text.split())})


def enable_retrieval(services: Services) -> None:
    """Hosted OpenAI with a budget, retrieval configured, and both suites marked evaluated."""
    services.settings = replace(
        services.settings,
        ai_enabled=True,
        ai_evaluated=True,
        ai_provider="openai",
        ai_model="test-model",
        openai_api_key="test-key",
        ai_budget_durable=True,
        ai_daily_turns=100,
        ai_daily_budget_microusd=1_000_000,
        ai_input_microusd_per_million=1_000_000,
        ai_output_microusd_per_million=1_000_000,
        rag_enabled=True,
        rag_evaluated=True,
        rag_vector_store_id=STORE_ID,
        rag_corpus_version=CORPUS_VERSION,
        rag_search_microusd_per_call=SEARCH_PRICE,
        rag_manifest_version=CORPUS_VERSION,
        discovery_evaluated=True,
    )


def search_hit(section_id: str) -> dict[str, object]:
    source_id, _, text = SECTIONS[section_id]
    return {
        "file_id": f"file-{section_id}",
        "filename": f"{section_id}.txt",
        "score": 0.8,
        "attributes": {"source_id": source_id, "section_id": section_id, "kind": "agency"},
        "content": [{"type": "text", "text": text}],
    }


@dataclass
class FakeOpenAI:
    """Answers vector-store searches with `hits` and Responses calls with `output`.

    `output` is the JSON object the model returns, or a whole Responses body when
    `raw_body` is set, for refusals and incomplete answers.
    """

    hits: Sequence[dict[str, object]] = ()
    output: object = None
    raw_body: dict[str, object] | None = None
    searches: list[dict[str, object]] = field(default_factory=list)
    generations: list[dict[str, object]] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.path.endswith("/search"):
            self.searches.append(body)
            return httpx.Response(200, json={"data": list(self.hits)})
        self.generations.append(body)
        if self.raw_body is not None:
            return httpx.Response(200, json=self.raw_body)
        text = self.output if isinstance(self.output, str) else json.dumps(self.output)
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
            },
        )

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        original = httpx.AsyncClient
        monkeypatch.setattr(
            ai.httpx,
            "AsyncClient",
            lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(self.handle)),
        )
