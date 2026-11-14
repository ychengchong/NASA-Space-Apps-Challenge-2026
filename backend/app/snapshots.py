"""Content-addressed raw responses and normalized series. Existing evidence is never replaced."""

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from threading import RLock

from app.errors import BadRequestError, SourceUnavailableError
from app.sources.base import PointSeries

SNAPSHOT_ID = re.compile(r"^[0-9a-f]{64}$")


def publish_once(path: Path, content: bytes) -> None:
    """Publish complete bytes atomically without replacing an existing file, across processes."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    except FileExistsError:
        pass
    finally:
        temporary.unlink()


class SnapshotStore:
    """Persistent immutable bytes, or in-memory bytes for isolated tests."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root
        self._memory: dict[str, bytes] = {}
        self._lock = RLock()
        if root is not None:
            root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes) -> str:
        """Retain exact bytes under their SHA-256; concurrent equal writes are harmless."""
        identity = hashlib.sha256(content).hexdigest()
        with self._lock:
            if self.root is None:
                self._memory.setdefault(identity, content)
            else:
                path = self.root / f"{identity}.json"
                if not path.exists():
                    publish_once(path, content)
                if path.read_bytes() != content:
                    raise SourceUnavailableError("Stored evidence failed integrity verification.")
        return identity

    def get(self, identity: str) -> bytes:
        """Read verified evidence; never substitute live data when a pinned snapshot is missing."""
        if not SNAPSHOT_ID.fullmatch(identity):
            raise BadRequestError("A snapshot ID must be a SHA-256 hexadecimal digest.")
        with self._lock:
            try:
                content = (
                    self._memory[identity]
                    if self.root is None
                    else (self.root / f"{identity}.json").read_bytes()
                )
            except (KeyError, OSError) as error:
                raise SourceUnavailableError(
                    "This pinned evidence is unavailable; no live data was substituted."
                ) from error
        if hashlib.sha256(content).hexdigest() != identity:
            raise SourceUnavailableError("Stored evidence failed integrity verification.")
        return content

    def freeze(self, series: PointSeries) -> str:
        """Freeze normalized monthly data and metadata, with a raw digest when retained."""
        value = asdict(series)
        value["monthly"] = {
            f"{year:04d}-{month:02d}": item
            for (year, month), item in sorted(series.monthly.items())
        }
        document = {"schema": "power_series_v1", "series": value}
        return self.put(
            json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        )

    def series(self, identity: str) -> PointSeries:
        """Reopen a normalized series; reject raw-response or unknown snapshot schemas."""
        try:
            document = json.loads(self.get(identity))
            if not isinstance(document, dict) or document.get("schema") != "power_series_v1":
                raise ValueError("Not a normalized series")
            value = document["series"]
            monthly = {(int(key[:4]), int(key[5:])): item for key, item in value["monthly"].items()}
            return PointSeries(**{**value, "monthly": monthly})
        except (ValueError, KeyError, TypeError) as error:
            raise SourceUnavailableError("The pinned series cannot be read.") from error
