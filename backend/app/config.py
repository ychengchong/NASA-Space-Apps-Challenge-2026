"""Settings read from environment variables (spec 11, "Configuration")."""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
FRONTEND_DIST_DIR = BACKEND_DIR.parent / "frontend" / "dist"

AiProvider = Literal["disabled", "ollama", "anthropic", "openai"]
AI_PROVIDERS: tuple[AiProvider, ...] = ("disabled", "ollama", "anthropic", "openai")


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
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
