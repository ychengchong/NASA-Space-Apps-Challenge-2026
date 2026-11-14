"""Settings read from environment variables (spec 11, "Configuration")."""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
FRONTEND_DIST_DIR = BACKEND_DIR.parent / "frontend" / "dist"

AiProvider = Literal["anthropic", "openai"]
AI_PROVIDERS: tuple[AiProvider, ...] = ("anthropic", "openai")
# Spec 11: the model the AI uses when AI_MODEL is not set.
DEFAULT_AI_MODELS: dict[AiProvider, str] = {
    "anthropic": "claude-opus-5-5",
    "openai": "gpt-6-luna",
}


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


def _provider_with_a_key(anthropic_api_key: str | None, openai_api_key: str | None) -> AiProvider:
    """Spec 11: with AI_PROVIDER unset, Claude when its key is set, otherwise OpenAI when its key
    is set. With neither key the AI is off; Claude is then returned only so that the settings
    name a model.
    """
    if anthropic_api_key is None and openai_api_key is not None:
        return "openai"
    return "anthropic"


@dataclass(frozen=True)
class Settings:
    # Left out of the repr, so a log line or a traceback that prints the settings never holds it.
    anthropic_api_key: str | None = field(repr=False)
    ai_enabled: bool
    # AI_MODEL, or the default model of `ai_provider`.
    ai_model: str
    ai_max_iterations: int
    ai_max_turns: int
    ai_daily_turns: int
    ai_rate_per_minute: int
    rate_limit_per_minute: int
    public_base_url: str | None
    cache_path: Path
    # AI_PROVIDER, or else the provider whose key is set (spec 11). The AI runs only when this
    # provider's key is set: see `active_ai_provider`.
    ai_provider: AiProvider = "anthropic"
    # Left out of the repr, as the Anthropic key is.
    openai_api_key: str | None = field(default=None, repr=False)

    @property
    def active_ai_provider(self) -> AiProvider | None:
        """The provider the AI runs on; None when the AI is turned off or that provider's key
        is not set (spec 8, "When the AI is off").
        """
        if not self.ai_enabled:
            return None
        key = self.openai_api_key if self.ai_provider == "openai" else self.anthropic_api_key
        return self.ai_provider if key is not None else None


def load_settings() -> Settings:
    public_base_url = _env_str("PUBLIC_BASE_URL")
    cache_path = _env_str("CACHE_PATH")
    anthropic_api_key = _env_str("ANTHROPIC_API_KEY")
    openai_api_key = _env_str("OPENAI_API_KEY")
    ai_provider = _env_provider("AI_PROVIDER") or _provider_with_a_key(
        anthropic_api_key, openai_api_key
    )
    return Settings(
        anthropic_api_key=anthropic_api_key,
        ai_enabled=_env_bool("AI_ENABLED", True),
        ai_model=_env_str("AI_MODEL") or DEFAULT_AI_MODELS[ai_provider],
        ai_max_iterations=_env_int("AI_MAX_ITERATIONS", 6),
        ai_max_turns=_env_int("AI_MAX_TURNS", 20),
        ai_daily_turns=_env_int("AI_DAILY_TURNS", 500),
        ai_rate_per_minute=_env_int("AI_RATE_PER_MINUTE", 10),
        rate_limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 120),
        public_base_url=public_base_url.rstrip("/") if public_base_url else None,
        cache_path=Path(cache_path) if cache_path else DATA_DIR / "cache.sqlite",
        ai_provider=ai_provider,
        openai_api_key=openai_api_key,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
