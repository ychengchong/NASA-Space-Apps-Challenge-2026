"""The corpus upload script (spec 8, "Planned corpus and retrieval"), against a fake OpenAI API."""

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import CORPUS_MANIFEST_PATH
from scripts.upload_corpus import (
    POLL_INTERVAL_SECONDS,
    POLL_LIMIT_SECONDS,
    STORE_EXPIRY_DAYS,
    SUPERSEDED_KEY,
    UploadError,
    load_manifest,
    main,
    openai_client,
    provider_message,
    run,
    store_name,
)

VERSION = "a" * 64
# The two section files of `_write_corpus`, "POWER text." and "Project note.", in bytes.
CORPUS_BYTES = 24
USAGE_BYTES = 4096


def _write_corpus(corpus_dir: Path) -> Path:
    """A two-section corpus from two sources, one agency and one project."""
    sections_dir = corpus_dir / "sections"
    sections_dir.mkdir(parents=True)
    texts = {"power-a-01": "POWER text.", "note-b-01": "Project note."}
    for section_id, text in texts.items():
        (sections_dir / f"{section_id}.txt").write_text(text, encoding="utf-8")
    manifest = {
        "corpus_version": VERSION,
        "sources": [
            {"source_id": "power-a", "kind": "agency"},
            {"source_id": "note-b", "kind": "project"},
        ],
        "sections": [
            {
                "section_id": section_id,
                "source_id": section_id.rsplit("-", 1)[0],
                "path": f"sections/{section_id}.txt",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
            for section_id, text in texts.items()
        ],
    }
    path = corpus_dir / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class FakeOpenAI:
    """Records requests and answers like the Files and Vector Stores endpoints."""

    def __init__(
        self,
        counts: list[dict[str, int]] | None = None,
        fail_store: bool = False,
        store_id: str = "vs_test",
        first_file: int = 1,
    ):
        self.requests: list[httpx.Request] = []
        self.counts = counts or [_counts(completed=2)]
        self.fail_store = fail_store
        self.store_id = store_id
        self.uploaded = first_file - 1

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "POST" and path == "/v1/files":
            self.uploaded += 1
            return httpx.Response(200, json={"id": f"file-{self.uploaded}"})
        if request.method == "POST" and path == "/v1/vector_stores":
            if self.fail_store:
                return httpx.Response(500, json={"error": {"message": "boom"}})
            return httpx.Response(200, json={"id": self.store_id})
        if request.method == "POST" and path == f"/v1/vector_stores/{self.store_id}/files":
            return httpx.Response(200, json={"id": json.loads(request.content)["file_id"]})
        if request.method == "GET" and path == f"/v1/vector_stores/{self.store_id}":
            counts = self.counts.pop(0) if len(self.counts) > 1 else self.counts[0]
            body = {"id": self.store_id, "file_counts": counts, "usage_bytes": USAGE_BYTES}
            return httpx.Response(200, json=body)
        return httpx.Response(404)

    def bodies(self, method: str, path: str) -> list[dict[str, Any]]:
        return [
            json.loads(request.content)
            for request in self.requests
            if request.method == method and request.url.path == path
        ]


def _counts(completed: int = 0, in_progress: int = 0, failed: int = 0) -> dict[str, int]:
    return {
        "completed": completed,
        "in_progress": in_progress,
        "failed": failed,
        "cancelled": 0,
        "total": completed + in_progress + failed,
    }


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def _run(
    tmp_path: Path,
    fake: FakeOpenAI,
    force: bool = False,
    clock: FakeClock | None = None,
    max_bytes: int = 1_000_000,
) -> tuple[Any, Path]:
    manifest_path = tmp_path / "corpus" / "manifest.json"
    if not manifest_path.exists():
        _write_corpus(tmp_path / "corpus")
    state_path = tmp_path / "state" / "corpus-files.json"
    clock = clock or FakeClock()
    with openai_client("test-key", httpx.MockTransport(fake)) as client:
        upload = run(
            client, manifest_path, state_path, force, max_bytes, sleep=clock.sleep, clock=clock
        )
    return upload, state_path


def _state(tmp_path: Path) -> dict[str, Any]:
    state: dict[str, Any] = json.loads((tmp_path / "state" / "corpus-files.json").read_text())
    return state


def test_store_name_uses_first_twelve_characters_of_version() -> None:
    assert store_name("0123456789abcdef") == "trend-detective-corpus-0123456789ab"


def test_each_section_is_uploaded_with_purpose_assistants(tmp_path: Path) -> None:
    fake = FakeOpenAI()
    _run(tmp_path, fake)
    uploads = [r for r in fake.requests if r.url.path == "/v1/files"]
    assert len(uploads) == 2
    assert all(b'name="purpose"\r\n\r\nassistants' in r.content for r in uploads)
    assert b'filename="power-a-01.txt"' in uploads[0].content
    assert b"POWER text." in uploads[0].content


def test_requests_carry_the_key_as_a_bearer_token(tmp_path: Path) -> None:
    fake = FakeOpenAI()
    _run(tmp_path, fake)
    assert {r.headers["authorization"] for r in fake.requests} == {"Bearer test-key"}


def test_store_is_named_by_version_and_expires_after_last_use(tmp_path: Path) -> None:
    fake = FakeOpenAI()
    _run(tmp_path, fake)
    assert fake.bodies("POST", "/v1/vector_stores") == [
        {
            "name": "trend-detective-corpus-aaaaaaaaaaaa",
            "expires_after": {"anchor": "last_active_at", "days": STORE_EXPIRY_DAYS},
        }
    ]


def test_files_are_attached_with_source_section_and_kind(tmp_path: Path) -> None:
    fake = FakeOpenAI()
    _run(tmp_path, fake)
    assert fake.bodies("POST", "/v1/vector_stores/vs_test/files") == [
        {
            "file_id": "file-1",
            "attributes": {"source_id": "power-a", "section_id": "power-a-01", "kind": "agency"},
        },
        {
            "file_id": "file-2",
            "attributes": {"source_id": "note-b", "section_id": "note-b-01", "kind": "project"},
        },
    ]


def test_state_maps_version_to_store_and_file_ids(tmp_path: Path) -> None:
    upload, state_path = _run(tmp_path, FakeOpenAI())
    assert upload.vector_store_id == "vs_test"
    assert json.loads(state_path.read_text()) == {
        VERSION: {
            "vector_store_id": "vs_test",
            "store_name": "trend-detective-corpus-aaaaaaaaaaaa",
            "complete": True,
            "files": {"note-b-01": "file-2", "power-a-01": "file-1"},
            "section_bytes": CORPUS_BYTES,
            "max_bytes": 1_000_000,
            "usage_bytes": USAGE_BYTES,
        }
    }


def test_a_corpus_over_the_byte_cap_is_refused_before_any_call(tmp_path: Path) -> None:
    fake = FakeOpenAI()
    with pytest.raises(UploadError, match="over the --max-bytes cap"):
        _run(tmp_path, fake, max_bytes=CORPUS_BYTES - 1)
    assert fake.requests == []
    assert not (tmp_path / "state" / "corpus-files.json").exists()


def test_a_corpus_at_the_byte_cap_is_uploaded(tmp_path: Path) -> None:
    upload, _ = _run(tmp_path, FakeOpenAI(), max_bytes=CORPUS_BYTES)
    assert upload.complete


def test_the_byte_cap_is_required_on_the_command_line(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--manifest", str(tmp_path / "manifest.json")])


def test_a_forced_upload_keeps_the_earlier_store_and_files(tmp_path: Path) -> None:
    _run(tmp_path, FakeOpenAI())
    _run(tmp_path, FakeOpenAI(store_id="vs_second", first_file=3), force=True)
    state = _state(tmp_path)
    assert state[VERSION]["vector_store_id"] == "vs_second"
    (earlier,) = state[SUPERSEDED_KEY]
    assert earlier["corpus_version"] == VERSION
    assert earlier["vector_store_id"] == "vs_test"
    assert earlier["files"] == {"note-b-01": "file-2", "power-a-01": "file-1"}


def test_a_retried_incomplete_upload_keeps_the_failed_attempt(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        _run(tmp_path, FakeOpenAI(counts=[_counts(failed=2)]))
    _run(tmp_path, FakeOpenAI(store_id="vs_second", first_file=3))
    state = _state(tmp_path)
    assert state[VERSION]["complete"] is True
    (earlier,) = state[SUPERSEDED_KEY]
    assert (earlier["vector_store_id"], earlier["complete"]) == ("vs_test", False)
    assert earlier["files"] == {"note-b-01": "file-2", "power-a-01": "file-1"}


def test_missing_manifest_is_refused_before_any_call(tmp_path: Path) -> None:
    with pytest.raises(UploadError, match="cannot be read"):
        load_manifest(tmp_path / "corpus" / "manifest.json")


def test_manifest_that_is_not_json_is_refused(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(UploadError, match="cannot be read as JSON"):
        load_manifest(manifest_path)


def test_manifest_missing_a_key_is_refused(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"corpus_version": VERSION}), encoding="utf-8")
    with pytest.raises(UploadError, match="malformed"):
        load_manifest(manifest_path)


def test_manifest_without_sections_is_refused_before_any_call(tmp_path: Path) -> None:
    manifest_path = _write_corpus(tmp_path / "corpus")
    manifest = json.loads(manifest_path.read_text())
    manifest["sections"] = []
    manifest_path.write_text(json.dumps(manifest))
    fake = FakeOpenAI()
    with pytest.raises(UploadError, match="no sections"):
        _run(tmp_path, fake)
    assert fake.requests == []


def test_corrupt_state_file_is_refused_and_kept(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "corpus-files.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{broken", encoding="utf-8")
    fake = FakeOpenAI()
    with pytest.raises(UploadError, match="state file"):
        _run(tmp_path, fake)
    assert fake.requests == []
    assert state_path.read_text(encoding="utf-8") == "{broken"


def test_command_line_reports_a_missing_manifest_without_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    code = main(
        [
            "--manifest",
            str(tmp_path / "missing.json"),
            "--state",
            str(tmp_path / "state.json"),
            "--max-bytes",
            "1000",
        ]
    )
    assert code == 1
    assert "Upload failed: The manifest" in capsys.readouterr().err


def test_polling_waits_until_all_files_are_completed(tmp_path: Path) -> None:
    fake = FakeOpenAI(counts=[_counts(in_progress=2), _counts(1, 1), _counts(completed=2)])
    clock = FakeClock()
    upload, _ = _run(tmp_path, fake, clock=clock)
    assert upload.complete
    assert clock.sleeps == [POLL_INTERVAL_SECONDS, POLL_INTERVAL_SECONDS]


def test_polling_stops_after_the_time_limit(tmp_path: Path) -> None:
    fake = FakeOpenAI(counts=[_counts(in_progress=2)])
    clock = FakeClock()
    with pytest.raises(UploadError, match="did not finish"):
        _run(tmp_path, fake, clock=clock)
    assert clock.now == pytest.approx(POLL_LIMIT_SECONDS, abs=POLL_INTERVAL_SECONDS)


def test_failed_indexing_is_an_error_and_recorded_incomplete(tmp_path: Path) -> None:
    fake = FakeOpenAI(counts=[_counts(completed=1, failed=1)])
    with pytest.raises(UploadError, match="1 failed"):
        _run(tmp_path, fake)
    state = json.loads((tmp_path / "state" / "corpus-files.json").read_text())
    assert state[VERSION]["complete"] is False
    assert state[VERSION]["vector_store_id"] == "vs_test"


def test_files_uploaded_before_a_failure_are_recorded_for_cleanup(tmp_path: Path) -> None:
    with pytest.raises(httpx.HTTPStatusError):
        _run(tmp_path, FakeOpenAI(fail_store=True))
    state = json.loads((tmp_path / "state" / "corpus-files.json").read_text())
    assert state[VERSION]["files"] == {"note-b-01": "file-2", "power-a-01": "file-1"}
    assert state[VERSION]["vector_store_id"] is None


def test_a_completed_version_is_refused_before_any_call(tmp_path: Path) -> None:
    _run(tmp_path, FakeOpenAI())
    fake = FakeOpenAI()
    with pytest.raises(UploadError, match="already uploaded to vs_test"):
        _run(tmp_path, fake)
    assert fake.requests == []


def test_force_uploads_a_completed_version_again(tmp_path: Path) -> None:
    _run(tmp_path, FakeOpenAI())
    fake = FakeOpenAI()
    upload, _ = _run(tmp_path, fake, force=True)
    assert upload.complete
    assert fake.uploaded == 2


def test_an_incomplete_version_may_be_uploaded_again(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        _run(tmp_path, FakeOpenAI(counts=[_counts(failed=2)]))
    upload, _ = _run(tmp_path, FakeOpenAI())
    assert upload.complete


def test_other_versions_in_state_are_kept(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "corpus-files.json"
    state_path.parent.mkdir(parents=True)
    older = {"vector_store_id": "vs_old", "store_name": "old", "complete": True, "files": {}}
    state_path.write_text(json.dumps({"b" * 64: older}))
    _run(tmp_path, FakeOpenAI())
    assert json.loads(state_path.read_text())["b" * 64] == older


def test_a_changed_section_file_is_refused(tmp_path: Path) -> None:
    manifest_path = _write_corpus(tmp_path / "corpus")
    (tmp_path / "corpus" / "sections" / "note-b-01.txt").write_text("Edited.", encoding="utf-8")
    with pytest.raises(UploadError, match="note-b-01 does not match"):
        load_manifest(manifest_path)


def test_a_manifest_without_version_is_refused(tmp_path: Path) -> None:
    manifest_path = _write_corpus(tmp_path / "corpus")
    manifest = json.loads(manifest_path.read_text())
    manifest["corpus_version"] = ""
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(UploadError, match="no corpus_version"):
        load_manifest(manifest_path)


def test_provider_message_redacts_key_shaped_text() -> None:
    response = httpx.Response(
        401, json={"error": {"message": "Incorrect API key provided: sk-proj-abc123."}}
    )
    assert provider_message(response) == "Incorrect API key provided: [redacted]"


def test_provider_message_without_json_body() -> None:
    assert provider_message(httpx.Response(502, text="Bad gateway")) == "no error message"


def test_committed_manifest_matches_its_section_files() -> None:
    manifest = load_manifest(CORPUS_MANIFEST_PATH)
    assert len(manifest["sections"]) > 0
