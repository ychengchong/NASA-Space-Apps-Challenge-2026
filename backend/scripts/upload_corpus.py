"""Upload the built corpus to an OpenAI vector store (spec 8, "Planned corpus and retrieval").

The script reads `data/corpus/manifest.json`, checks every section file against its recorded
SHA-256, and then:

1. uploads each section file to OpenAI Files with purpose "assistants";
2. creates a vector store named `trend-detective-corpus-<first 12 characters of the version>`
   that expires 30 days after it was last used;
3. attaches each file with the attributes `source_id`, `section_id` and `kind`, which the
   server uses to cite the passage;
4. polls the store's file counts until every file is indexed, or a bounded time has passed;
5. records the file IDs, the uploaded byte count and the store's reported storage size in
   `state/corpus-files.json` (operational state, not committed), and prints the vector store
   ID and corpus version to set as RAG_VECTOR_STORE_ID and RAG_CORPUS_VERSION.

Spec 8, "Bounds and evaluation": ingestion and storage costs are capped separately from public
requests. Both grow with the uploaded bytes, so the owner passes `--max-bytes`, and a corpus
whose section files are larger in total is refused before any call.

It refuses to upload a corpus version that the state file already records as complete,
unless `--force` is given. A repeated upload of a version keeps the earlier attempt under
`superseded` in the state file. Run from backend/ with the key in the environment:

    uv run --env-file ../.env python -m scripts.upload_corpus --max-bytes 1000000

Cleanup: an unused store expires by itself after 30 days, but its files do not. To remove an
upload, delete the store (DELETE /v1/vector_stores/{id}) and each file listed for that version,
or for a superseded attempt, in the state file (DELETE /v1/files/{id}).
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.config import BACKEND_DIR, CORPUS_MANIFEST_PATH

STATE_PATH = BACKEND_DIR.parent / "state" / "corpus-files.json"
OPENAI_API_URL = "https://api.openai.com/v1"
STORE_NAME_PREFIX = "trend-detective-corpus-"
VERSION_PREFIX_CHARACTERS = 12
# An unused store is deleted by OpenAI after this many days, so a forgotten upload stops
# costing storage on its own.
STORE_EXPIRY_DAYS = 30
REQUEST_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 2.0
POLL_LIMIT_SECONDS = 600.0
# The state-file key under which earlier attempts at an uploaded version are kept.
SUPERSEDED_KEY = "superseded"

# Provider error messages can echo part of a key; never print one.
_API_KEY = re.compile(r"sk-\S+")

Sleep = Callable[[float], None]
Clock = Callable[[], float]


class UploadError(Exception):
    """The corpus cannot be uploaded, or the upload did not finish indexing."""


@dataclass
class Upload:
    """What one run uploaded, kept for the state file even when the run fails part-way."""

    corpus_version: str
    store_name: str
    section_bytes: int
    max_bytes: int
    vector_store_id: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    # The store's own storage size once indexed, as the provider reports it; None until then.
    usage_bytes: int | None = None
    complete: bool = False

    def as_state(self) -> dict[str, Any]:
        """The state-file entry of this upload."""
        return {
            "vector_store_id": self.vector_store_id,
            "store_name": self.store_name,
            "complete": self.complete,
            "files": dict(sorted(self.files.items())),
            "section_bytes": self.section_bytes,
            "max_bytes": self.max_bytes,
            "usage_bytes": self.usage_bytes,
        }


def store_name(corpus_version: str) -> str:
    """The vector store name for a corpus version: the prefix and the version's first 12 chars."""
    return STORE_NAME_PREFIX + corpus_version[:VERSION_PREFIX_CHARACTERS]


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """The manifest, after checking that every section file matches its recorded SHA-256.

    Raises `UploadError` for a missing, unreadable or malformed manifest, a missing version, a
    manifest without sections, an unknown source or a missing or changed section file, so the
    store never holds text that differs from the manifest it is named after.
    """
    manifest = _read_json(manifest_path, "manifest")
    if not isinstance(manifest, dict):
        raise UploadError("The manifest is not a JSON object.")
    try:
        _check_manifest(manifest, manifest_path.parent)
    except (KeyError, TypeError) as error:
        raise UploadError(f"The manifest is malformed: {error!r}.") from error
    except OSError as error:
        raise UploadError(f"A section file cannot be read: {error}") from error
    return manifest


def _check_manifest(manifest: dict[str, Any], corpus_dir: Path) -> None:
    if not isinstance(manifest.get("corpus_version"), str) or not manifest["corpus_version"]:
        raise UploadError("The manifest has no corpus_version.")
    if not manifest["sections"]:
        raise UploadError("The manifest has no sections; build the corpus first.")
    kinds = {source["source_id"]: source["kind"] for source in manifest["sources"]}
    for section in manifest["sections"]:
        if section["source_id"] not in kinds:
            raise UploadError(f"Section {section['section_id']} names an unknown source.")
        content = (corpus_dir / section["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != section["sha256"]:
            raise UploadError(f"Section {section['section_id']} does not match the manifest.")


def section_bytes(manifest: dict[str, Any], corpus_dir: Path) -> int:
    """The total size in bytes of the section files `manifest` lists."""
    return sum((corpus_dir / section["path"]).stat().st_size for section in manifest["sections"])


def read_state(state_path: Path) -> dict[str, Any]:
    """The state file's uploads by corpus version, or an empty mapping when there is none.

    Raises `UploadError` for a state file that cannot be read or is not a JSON object, so a
    damaged record of earlier uploads is never overwritten.
    """
    if not state_path.exists():
        return {}
    state = _read_json(state_path, "state file")
    if not isinstance(state, dict):
        raise UploadError("The state file is not a JSON object.")
    return state


def _read_json(path: Path, name: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UploadError(f"The {name} {path} cannot be read as JSON: {error}") from error


def write_state(state_path: Path, state: dict[str, Any]) -> None:
    """Write the state file, creating the state directory when needed."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upload_corpus(
    client: httpx.Client,
    manifest: dict[str, Any],
    corpus_dir: Path,
    upload: Upload,
    sleep: Sleep = time.sleep,
    clock: Clock = time.monotonic,
) -> None:
    """Upload, attach and index every section of `manifest`, filling `upload` as it goes.

    `upload` is filled step by step, so a caller can record what exists after a failure.
    Raises `UploadError` when indexing fails or does not finish within `POLL_LIMIT_SECONDS`,
    and `httpx.HTTPError` for a failed call. No call is retried.
    """
    kinds = {source["source_id"]: source["kind"] for source in manifest["sources"]}
    for section in manifest["sections"]:
        upload.files[section["section_id"]] = _upload_file(client, corpus_dir / section["path"])
    upload.vector_store_id = _create_store(client, upload.store_name)
    for section in manifest["sections"]:
        attributes = {
            "source_id": section["source_id"],
            "section_id": section["section_id"],
            "kind": kinds[section["source_id"]],
        }
        _attach_file(
            client, upload.vector_store_id, upload.files[section["section_id"]], attributes
        )
    store = _wait_for_indexing(
        client, upload.vector_store_id, len(manifest["sections"]), sleep, clock
    )
    usage_bytes = store.get("usage_bytes")
    upload.usage_bytes = usage_bytes if isinstance(usage_bytes, int) else None
    upload.complete = True


def _upload_file(client: httpx.Client, path: Path) -> str:
    response = client.post(
        "/files",
        data={"purpose": "assistants"},
        files={"file": (path.name, path.read_bytes(), "text/plain")},
    )
    response.raise_for_status()
    return str(response.json()["id"])


def _create_store(client: httpx.Client, name: str) -> str:
    response = client.post(
        "/vector_stores",
        json={
            "name": name,
            "expires_after": {"anchor": "last_active_at", "days": STORE_EXPIRY_DAYS},
        },
    )
    response.raise_for_status()
    return str(response.json()["id"])


def _attach_file(
    client: httpx.Client, vector_store_id: str, file_id: str, attributes: dict[str, str]
) -> None:
    response = client.post(
        f"/vector_stores/{vector_store_id}/files",
        json={"file_id": file_id, "attributes": attributes},
    )
    response.raise_for_status()


def _wait_for_indexing(
    client: httpx.Client, vector_store_id: str, expected: int, sleep: Sleep, clock: Clock
) -> dict[str, Any]:
    """Poll the store's file counts until all `expected` files are indexed, failed or timed out.

    Returns the store as last read, once every file is indexed.
    """
    deadline = clock() + POLL_LIMIT_SECONDS
    while True:
        response = client.get(f"/vector_stores/{vector_store_id}")
        response.raise_for_status()
        store: dict[str, Any] = response.json()
        counts = store["file_counts"]
        if counts["failed"] or counts["cancelled"]:
            raise UploadError(
                f"Indexing stopped: {counts['failed']} failed, {counts['cancelled']} cancelled."
            )
        if counts["in_progress"] == 0 and counts["completed"] == expected:
            return store
        if clock() >= deadline:
            raise UploadError(
                f"Indexing did not finish in {POLL_LIMIT_SECONDS:.0f} s: "
                f"{counts['completed']} of {expected} completed."
            )
        sleep(POLL_INTERVAL_SECONDS)


def openai_client(api_key: str, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """An OpenAI API client with a timeout and no redirects or proxy environment."""
    return httpx.Client(
        base_url=OPENAI_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
        transport=transport,
    )


def run(
    client: httpx.Client,
    manifest_path: Path,
    state_path: Path,
    force: bool,
    max_bytes: int,
    sleep: Sleep = time.sleep,
    clock: Clock = time.monotonic,
) -> Upload:
    """Upload the corpus of `manifest_path` and record the result in `state_path`.

    Refuses (with `UploadError`, before any call) a corpus whose section files exceed
    `max_bytes` in total, and a version the state file records as complete unless `force`.
    The state entry is written even when the upload fails part-way, and an earlier entry for
    the same version moves to `superseded`, so every file and store created can be found and
    deleted.
    """
    manifest = load_manifest(manifest_path)
    version = manifest["corpus_version"]
    total_bytes = section_bytes(manifest, manifest_path.parent)
    if total_bytes > max_bytes:
        raise UploadError(
            f"The corpus is {total_bytes} bytes, over the --max-bytes cap of {max_bytes}."
        )
    state = read_state(state_path)
    previous = state.get(version)
    if isinstance(previous, dict) and previous.get("complete") and not force:
        raise UploadError(
            f"Corpus {version} is already uploaded to {previous['vector_store_id']}; "
            "pass --force to upload it again."
        )
    upload = Upload(
        corpus_version=version,
        store_name=store_name(version),
        section_bytes=total_bytes,
        max_bytes=max_bytes,
    )
    try:
        upload_corpus(client, manifest, manifest_path.parent, upload, sleep, clock)
    finally:
        if isinstance(previous, dict):
            state.setdefault(SUPERSEDED_KEY, []).append({"corpus_version": version, **previous})
        state[version] = upload.as_state()
        write_state(state_path, state)
    return upload


def provider_message(response: httpx.Response) -> str:
    """The provider's error message, with anything shaped like an API key redacted."""
    try:
        message = str(response.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        message = "no error message"
    return _API_KEY.sub("[redacted]", message)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.upload_corpus",
        description="Upload the corpus sections to a new OpenAI vector store.",
    )
    parser.add_argument("--manifest", type=Path, default=CORPUS_MANIFEST_PATH)
    parser.add_argument("--state", type=Path, default=STATE_PATH)
    parser.add_argument(
        "--force", action="store_true", help="upload again even if this version is recorded"
    )
    parser.add_argument(
        "--max-bytes",
        type=_positive_int,
        required=True,
        help="refuse a corpus whose section files exceed this many bytes in total",
    )
    args = parser.parse_args(argv)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1
    try:
        with openai_client(api_key) as client:
            upload = run(client, args.manifest, args.state, args.force, args.max_bytes)
    except httpx.HTTPStatusError as error:
        print(f"Upload failed: {error}: {provider_message(error.response)}", file=sys.stderr)
        return 1
    except (UploadError, httpx.HTTPError) as error:
        print(f"Upload failed: {error}", file=sys.stderr)
        return 1
    print(f"RAG_VECTOR_STORE_ID={upload.vector_store_id}")
    print(f"RAG_CORPUS_VERSION={upload.corpus_version}")
    print(
        f"{len(upload.files)} files ({upload.section_bytes} bytes) indexed; store usage "
        f"{upload.usage_bytes} bytes; IDs recorded in {args.state}"
    )
    return 0


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive number of bytes")
    return number


if __name__ == "__main__":
    sys.exit(main())
