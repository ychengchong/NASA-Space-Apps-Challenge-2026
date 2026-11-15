"""Settings read from environment variables (spec 11, "Configuration")."""

import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
FRONTEND_DIST_DIR = BACKEND_DIR.parent / "frontend" / "dist"
# Spec 8, "Planned corpus and retrieval": the reviewed corpus manifest names its version.
CORPUS_MANIFEST_PATH = DATA_DIR / "corpus" / "manifest.json"
# The shape of an OpenAI vector store ID. A store ID of any other shape cannot be searched, so
# it turns discovery and explanation off (spec 8, "Bounds and evaluation").
VECTOR_STORE_ID_PATTERN = re.compile(r"^vs_[A-Za-z0-9_-]{1,128}$")
# Spec 8, "Planned explanations": the investigation lookup is bounded. A record holds a case
# query, whose place labels are user text, so it is kept one day and the table holds at most
# this many rows; opening the case again records it afresh.
INVESTIGATION_RETENTION_SECONDS = 24 * 60 * 60
MAX_RECORDED_INVESTIGATIONS = 10_000

AiProvider = Literal["disabled", "ollama", "anthropic", "openai"]
AI_PROVIDERS: tuple[AiProvider, ...] = ("disabled", "ollama", "anthropic", "openai")
# Owner decision, 15 November 2026: guided discovery and cited explanations are on by default
# wherever the AI and the corpus are configured (spec 8, "Bounds and evaluation").
AI_PATHS_ON_BY_DEFAULT = True


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_str(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.strip()


def _env_provider(name: str) -> AiProvider | None:
    """The provider named in `name`, or None when it is not set. Raises `ValueError` for any
    other value, so a typing mistake stops the server at start rather than turning the AI off.
    """
    raw = _env_str(name)
    if raw is None:
        return None
    for provider in AI_PROVIDERS:
        if raw == provider:
            return provider
    raise ValueError(f"{name} must be one of {', '.join(AI_PROVIDERS)}, not {raw!r}.")


def read_corpus_version(path: Path) -> str | None:
    """The `corpus_version` of the manifest at `path`; None when the file is unreadable, is not
    valid JSON or holds no non-empty string version. Discovery and explanation then stay off.
    """
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    version = manifest.get("corpus_version") if isinstance(manifest, dict) else None
    return version if isinstance(version, str) and version != "" else None


@dataclass(frozen=True)
class Settings:
    # Left out of the repr, so a log line or a traceback that prints the settings never holds it.
    anthropic_api_key: str | None = field(repr=False)
    ai_enabled: bool
    # Exact owner-selected model; no guessed default.
    ai_model: str
    ai_daily_turns: int
    ai_rate_per_minute: int
    rate_limit_per_minute: int
    public_base_url: str | None
    cache_path: Path
    # Provider selection and activation are explicit; credentials alone never activate AI.
    ai_provider: AiProvider = "disabled"
    # Left out of the repr, as the Anthropic key is.
    openai_api_key: str | None = field(default=None, repr=False)
    operational_path: Path = Path("state/operations.sqlite")
    snapshot_path: Path = Path("state/snapshots")
    ai_evaluated: bool = False
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_digest: str = ""
    ai_daily_budget_microusd: int = 0
    ai_input_microusd_per_million: int = 0
    ai_output_microusd_per_million: int = 0
    ai_budget_durable: bool = False
    # Spec 8, "Bounds and evaluation": retrieval has its own readiness and evaluation flags. The
    # owner turned discovery and explanations on by default on 15 November 2026, although their
    # evaluation gates were not met (docs/evaluation-results.md); each still needs the AI and the
    # corpus configured, and each can be turned off.
    rag_enabled: bool = AI_PATHS_ON_BY_DEFAULT
    rag_evaluated: bool = AI_PATHS_ON_BY_DEFAULT
    rag_vector_store_id: str = ""
    rag_corpus_version: str = ""
    # Integer microdollars per vector-store search call, supplied by the owner.
    rag_search_microusd_per_call: int = 0
    # The version the corpus manifest on disk declares; None when there is no manifest.
    rag_manifest_version: str | None = None
    discovery_evaluated: bool = AI_PATHS_ON_BY_DEFAULT

    @property
    def planner_available(self) -> bool:
        """Whether /api/plan can run (spec 8): some provider is active."""
        return self.active_ai_provider is not None

    @property
    def rag_configured(self) -> bool:
        """Whether retrieval is set up: enabled, a well-formed store ID, a priced search and a
        corpus version equal to the manifest's. A mismatch turns off only discovery and
        explanation (spec 8).
        """
        return (
            self.rag_enabled
            and VECTOR_STORE_ID_PATTERN.fullmatch(self.rag_vector_store_id) is not None
            and self.rag_corpus_version != ""
            and self.rag_search_microusd_per_call > 0
            and self.rag_manifest_version == self.rag_corpus_version
        )

    @property
    def discovery_available(self) -> bool:
        """Whether /api/discover can run: hosted OpenAI planning, retrieval set up, and the
        discovery suite evaluated (DISCOVERY_EVALUATED).
        """
        return (
            self.active_ai_provider == "openai" and self.rag_configured and self.discovery_evaluated
        )

    @property
    def explanation_available(self) -> bool:
        """Whether /api/explain can run: hosted OpenAI with the planner's budget and evaluation
        gates, retrieval set up, and the retrieval suite evaluated (RAG_EVALUATED).
        """
        return self.active_ai_provider == "openai" and self.rag_configured and self.rag_evaluated

    @property
    def active_ai_provider(self) -> AiProvider | None:
        """The provider the AI runs on; None when the AI is turned off or that provider's key
        is not set (spec 8, "When the AI is off").
        """
        if (
            not self.ai_enabled
            or not self.ai_evaluated
            or not self.ai_model
            or self.ai_provider == "disabled"
        ):
            return None
        if self.ai_provider == "ollama":
            return "ollama" if self.ollama_digest else None
        if (
            not self.ai_budget_durable
            or self.ai_daily_budget_microusd <= 0
            or self.ai_input_microusd_per_million <= 0
            or self.ai_output_microusd_per_million <= 0
        ):
            return None
        key = self.openai_api_key if self.ai_provider == "openai" else self.anthropic_api_key
        return self.ai_provider if key is not None else None


def load_settings() -> Settings:
    public_base_url = _env_str("PUBLIC_BASE_URL")
    cache_path = _env_str("CACHE_PATH")
    anthropic_api_key = _env_str("ANTHROPIC_API_KEY")
    openai_api_key = _env_str("OPENAI_API_KEY")
    ai_provider = _env_provider("AI_PROVIDER") or "disabled"
    return Settings(
        anthropic_api_key=anthropic_api_key,
        ai_enabled=_env_bool("AI_ENABLED", False),
        ai_model=_env_str("AI_MODEL") or "",
        ai_daily_turns=_env_int("AI_DAILY_TURNS", 500),
        ai_rate_per_minute=_env_int("AI_RATE_PER_MINUTE", 10),
        rate_limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 120),
        public_base_url=public_base_url.rstrip("/") if public_base_url else None,
        cache_path=Path(cache_path) if cache_path else BACKEND_DIR.parent / "state/power.sqlite",
        ai_provider=ai_provider,
        openai_api_key=openai_api_key,
        operational_path=Path(
            _env_str("OPERATIONAL_DB_PATH") or BACKEND_DIR.parent / "state/operations.sqlite"
        ),
        snapshot_path=Path(_env_str("SNAPSHOT_PATH") or BACKEND_DIR.parent / "state/snapshots"),
        ai_evaluated=_env_bool("AI_EVALUATED", False),
        ollama_url=_env_str("OLLAMA_URL") or "http://127.0.0.1:11434",
        ollama_digest=_env_str("OLLAMA_MODEL_DIGEST") or "",
        ai_daily_budget_microusd=_env_int("AI_DAILY_BUDGET_MICROUSD", 0),
        ai_input_microusd_per_million=_env_int("AI_INPUT_MICROUSD_PER_MILLION", 0),
        ai_output_microusd_per_million=_env_int("AI_OUTPUT_MICROUSD_PER_MILLION", 0),
        ai_budget_durable=_env_bool("AI_BUDGET_DURABLE", False),
        rag_enabled=_env_bool("RAG_ENABLED", AI_PATHS_ON_BY_DEFAULT),
        rag_evaluated=_env_bool("RAG_EVALUATED", AI_PATHS_ON_BY_DEFAULT),
        rag_vector_store_id=_env_str("RAG_VECTOR_STORE_ID") or "",
        rag_corpus_version=_env_str("RAG_CORPUS_VERSION") or "",
        rag_search_microusd_per_call=_env_int("RAG_SEARCH_MICROUSD_PER_CALL", 0),
        rag_manifest_version=read_corpus_version(CORPUS_MANIFEST_PATH),
        discovery_evaluated=_env_bool("DISCOVERY_EVALUATED", AI_PATHS_ON_BY_DEFAULT),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
