"""Settings and the container's configuration (spec 11, "Configuration" and "Deployment")."""

import pytest

from app.config import BACKEND_DIR, load_settings

API_KEY = "sk-ant-test-0123456789"
OPENAI_API_KEY = "sk-openai-test-0123456789"
DOCKERFILE = BACKEND_DIR.parent / "Dockerfile"
AI_SETTINGS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AI_PROVIDER", "AI_MODEL", "AI_ENABLED")


@pytest.fixture
def ai_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """The environment without any AI setting, so that each test sets only its own."""
    for name in AI_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_settings_repr_never_shows_the_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", API_KEY)

    settings = load_settings()

    assert settings.anthropic_api_key == API_KEY
    assert API_KEY not in repr(settings)


def test_settings_repr_never_shows_the_openai_api_key(ai_env: pytest.MonkeyPatch) -> None:
    ai_env.setenv("OPENAI_API_KEY", OPENAI_API_KEY)

    settings = load_settings()

    assert settings.openai_api_key == OPENAI_API_KEY
    assert OPENAI_API_KEY not in repr(settings)


# Which provider the AI runs on (spec 11, "Configuration")

BOTH_KEYS = {"ANTHROPIC_API_KEY": API_KEY, "OPENAI_API_KEY": OPENAI_API_KEY}


@pytest.mark.parametrize(
    ("env", "provider"),
    [
        pytest.param({"ANTHROPIC_API_KEY": API_KEY}, "anthropic", id="claude-key-alone"),
        pytest.param({"OPENAI_API_KEY": OPENAI_API_KEY}, "openai", id="openai-key-alone"),
        pytest.param(BOTH_KEYS, "anthropic", id="both-keys-claude-first"),
        pytest.param({}, None, id="no-key"),
        pytest.param({**BOTH_KEYS, "AI_PROVIDER": "openai"}, "openai", id="openai-named"),
        pytest.param({**BOTH_KEYS, "AI_PROVIDER": "anthropic"}, "anthropic", id="claude-named"),
        pytest.param(
            {"OPENAI_API_KEY": OPENAI_API_KEY, "AI_PROVIDER": "anthropic"},
            None,
            id="claude-named-without-its-key",
        ),
        pytest.param(
            {"ANTHROPIC_API_KEY": API_KEY, "AI_PROVIDER": "openai"},
            None,
            id="openai-named-without-its-key",
        ),
        pytest.param({**BOTH_KEYS, "AI_ENABLED": "false"}, None, id="ai-disabled"),
        pytest.param(
            {**BOTH_KEYS, "AI_PROVIDER": "openai", "AI_ENABLED": "false"},
            None,
            id="ai-disabled-with-a-named-provider",
        ),
    ],
)
def test_active_ai_provider_follows_the_named_provider_and_the_keys_set(
    ai_env: pytest.MonkeyPatch, env: dict[str, str], provider: str | None
) -> None:
    for name, value in env.items():
        ai_env.setenv(name, value)

    assert load_settings().active_ai_provider is None
    assert not load_settings().ai_evaluated


def test_unknown_ai_provider_is_a_configuration_error(ai_env: pytest.MonkeyPatch) -> None:
    ai_env.setenv("AI_PROVIDER", "gemini")

    with pytest.raises(ValueError, match="AI_PROVIDER"):
        load_settings()


@pytest.mark.parametrize(
    ("env", "model"),
    [
        pytest.param({"ANTHROPIC_API_KEY": API_KEY}, "claude-opus-5-5", id="claude"),
        pytest.param({"OPENAI_API_KEY": OPENAI_API_KEY}, "gpt-6-luna", id="openai"),
        pytest.param({**BOTH_KEYS, "AI_PROVIDER": "openai"}, "gpt-6-luna", id="openai-named"),
    ],
)
def test_default_model_is_the_one_of_the_provider_in_use(
    ai_env: pytest.MonkeyPatch, env: dict[str, str], model: str
) -> None:
    for name, value in env.items():
        ai_env.setenv(name, value)

    assert load_settings().ai_model == ""


@pytest.mark.parametrize("key", ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"])
def test_ai_model_overrides_the_default_model_of_either_provider(
    ai_env: pytest.MonkeyPatch, key: str
) -> None:
    ai_env.setenv(key, "test-key")
    ai_env.setenv("AI_MODEL", "some-other-model")

    assert load_settings().ai_model == "some-other-model"


def test_image_trusts_forwarded_addresses_from_loopback_alone_by_default() -> None:
    # uvicorn reads FORWARDED_ALLOW_IPS itself; a deploy sets it to the platform proxy's range.
    lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()

    assert "ENV FORWARDED_ALLOW_IPS=127.0.0.1" in lines


def test_start_command_leaves_the_trusted_proxy_addresses_to_the_environment() -> None:
    # A flag on the command line would override FORWARDED_ALLOW_IPS.
    assert "--forwarded-allow-ips" not in DOCKERFILE.read_text(encoding="utf-8")
