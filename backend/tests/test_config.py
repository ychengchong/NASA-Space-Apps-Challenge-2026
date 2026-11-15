"""Settings and the container's configuration (spec 11, "Configuration" and "Deployment")."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.config import BACKEND_DIR, Settings, load_settings, read_corpus_version

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


# Retrieval readiness for discovery and explanation (spec 8, "Bounds and evaluation")

CORPUS_VERSION = "c" * 64
RAG_ENV = ("RAG_ENABLED", "RAG_EVALUATED", "RAG_VECTOR_STORE_ID", "RAG_CORPUS_VERSION")


def hosted_settings(**changes: object) -> Settings:
    """Settings with the hosted OpenAI planner and retrieval fully configured, then `changes`."""
    ready = replace(
        load_settings(),
        ai_enabled=True,
        ai_evaluated=True,
        ai_provider="openai",
        ai_model="test-model",
        openai_api_key=OPENAI_API_KEY,
        ai_budget_durable=True,
        ai_daily_budget_microusd=1_000_000,
        ai_input_microusd_per_million=100_000,
        ai_output_microusd_per_million=500_000,
        rag_enabled=True,
        rag_evaluated=True,
        rag_vector_store_id="vs_test",
        rag_corpus_version=CORPUS_VERSION,
        rag_search_microusd_per_call=2500,
        rag_manifest_version=CORPUS_VERSION,
        discovery_evaluated=True,
    )
    return replace(ready, **changes)


def test_fully_configured_hosted_openai_offers_every_ai_path() -> None:
    settings = hosted_settings()

    assert settings.planner_available
    assert settings.discovery_available
    assert settings.explanation_available


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"rag_enabled": False}, id="rag-off"),
        pytest.param({"rag_vector_store_id": ""}, id="no-store"),
        pytest.param({"rag_vector_store_id": "vs-test"}, id="malformed-store-id"),
        pytest.param({"rag_vector_store_id": "vs_test/../files"}, id="store-id-with-path"),
        pytest.param({"rag_corpus_version": ""}, id="no-corpus-version"),
        pytest.param({"rag_search_microusd_per_call": 0}, id="no-search-price"),
        pytest.param({"rag_manifest_version": None}, id="no-manifest"),
        pytest.param({"rag_manifest_version": "d" * 64}, id="manifest-mismatch"),
    ],
)
def test_unready_retrieval_turns_off_only_discovery_and_explanation(
    changes: dict[str, object],
) -> None:
    settings = hosted_settings(**changes)

    assert settings.planner_available
    assert not settings.discovery_available
    assert not settings.explanation_available


NOT_OPENAI = "provider_not_openai"


@pytest.mark.parametrize(
    ("changes", "planner_gaps", "retrieval_gaps"),
    [
        pytest.param({"ai_enabled": False}, ["ai_disabled"], ["ai_disabled"], id="ai-off"),
        pytest.param(
            {"ai_provider": "disabled"}, ["no_ai_provider"], ["no_ai_provider"], id="no-provider"
        ),
        pytest.param(
            {"ai_evaluated": False}, ["ai_not_evaluated"], ["ai_not_evaluated"], id="not-evaluated"
        ),
        pytest.param({"ai_model": ""}, ["no_ai_model"], ["no_ai_model"], id="no-model"),
        pytest.param(
            {"openai_api_key": None},
            ["no_openai_api_key"],
            ["no_openai_api_key"],
            id="no-openai-key",
        ),
        pytest.param(
            {"ai_provider": "anthropic", "anthropic_api_key": None},
            ["no_anthropic_api_key"],
            ["no_anthropic_api_key", NOT_OPENAI],
            id="no-anthropic-key",
        ),
        pytest.param(
            {"ai_provider": "ollama", "ollama_digest": ""},
            ["no_ollama_digest"],
            ["no_ollama_digest", NOT_OPENAI],
            id="no-ollama-digest",
        ),
        pytest.param(
            {"ai_budget_durable": False},
            ["budget_not_durable"],
            ["budget_not_durable"],
            id="budget-not-durable",
        ),
        pytest.param(
            {"ai_daily_budget_microusd": 0},
            ["no_daily_budget"],
            ["no_daily_budget"],
            id="no-budget",
        ),
        pytest.param(
            {"ai_output_microusd_per_million": 0},
            ["no_token_prices"],
            ["no_token_prices"],
            id="no-prices",
        ),
        pytest.param(
            {"ai_provider": "anthropic", "anthropic_api_key": API_KEY},
            [],
            [NOT_OPENAI],
            id="anthropic",
        ),
        pytest.param({"rag_enabled": False}, [], ["rag_disabled"], id="rag-off"),
        pytest.param({"rag_vector_store_id": ""}, [], ["no_vector_store"], id="no-store"),
        pytest.param(
            {"rag_vector_store_id": "vs-test"}, [], ["malformed_vector_store"], id="malformed-id"
        ),
        pytest.param({"rag_corpus_version": ""}, [], ["no_corpus_version"], id="no-corpus-version"),
        pytest.param({"rag_manifest_version": None}, [], ["no_corpus_manifest"], id="no-manifest"),
        pytest.param(
            {"rag_corpus_version": CORPUS_VERSION[:-1]},
            [],
            ["corpus_version_mismatch"],
            id="version-cut-short",
        ),
        pytest.param(
            {"rag_search_microusd_per_call": 0}, [], ["no_search_price"], id="no-search-price"
        ),
    ],
)
def test_each_gap_names_the_setting_that_keeps_its_paths_off(
    changes: dict[str, object], planner_gaps: list[str], retrieval_gaps: list[str]
) -> None:
    settings = hosted_settings(**changes)

    assert settings.planner_gaps == planner_gaps
    assert settings.discovery_gaps == retrieval_gaps
    assert settings.explanation_gaps == retrieval_gaps
    assert settings.planner_available is (planner_gaps == [])


def test_each_evaluation_flag_is_a_gap_of_its_own_path_only() -> None:
    assert hosted_settings(discovery_evaluated=False).discovery_gaps == ["discovery_not_evaluated"]
    assert hosted_settings(discovery_evaluated=False).explanation_gaps == []
    assert hosted_settings(rag_evaluated=False).explanation_gaps == ["explanations_not_evaluated"]
    assert hosted_settings(rag_evaluated=False).discovery_gaps == []


def test_every_gap_is_listed_not_only_the_first() -> None:
    # A fresh .env.example with a key: the corpus upload's two values are still empty.
    settings = hosted_settings(rag_vector_store_id="", rag_corpus_version="")

    assert settings.planner_gaps == []
    assert settings.explanation_gaps == ["no_vector_store", "no_corpus_version"]
    assert not settings.explanation_available


def test_each_retrieval_path_has_its_own_evaluation_flag() -> None:
    assert not hosted_settings(discovery_evaluated=False).discovery_available
    assert hosted_settings(discovery_evaluated=False).explanation_available
    assert not hosted_settings(rag_evaluated=False).explanation_available
    assert hosted_settings(rag_evaluated=False).discovery_available


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"ai_provider": "anthropic", "anthropic_api_key": API_KEY}, id="anthropic"),
        pytest.param({"ai_provider": "ollama", "ollama_digest": "a" * 64}, id="ollama"),
        pytest.param({"ai_budget_durable": False}, id="no-durable-budget"),
        pytest.param({"ai_evaluated": False}, id="planner-not-evaluated"),
    ],
)
def test_discovery_and_explanation_need_the_hosted_openai_planner(
    changes: dict[str, object],
) -> None:
    settings = hosted_settings(**changes)

    assert not settings.discovery_available
    assert not settings.explanation_available


def test_retrieval_settings_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("RAG_EVALUATED", "true")
    monkeypatch.setenv("RAG_VECTOR_STORE_ID", "vs_abc")
    monkeypatch.setenv("RAG_CORPUS_VERSION", CORPUS_VERSION)
    monkeypatch.setenv("RAG_SEARCH_MICROUSD_PER_CALL", "2500")
    monkeypatch.setenv("DISCOVERY_EVALUATED", "true")

    settings = load_settings()

    assert settings.rag_enabled and settings.rag_evaluated and settings.discovery_evaluated
    assert settings.rag_vector_store_id == "vs_abc"
    assert settings.rag_corpus_version == CORPUS_VERSION
    assert settings.rag_search_microusd_per_call == 2500


def test_discovery_and_explanation_flags_are_on_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (*RAG_ENV, "RAG_SEARCH_MICROUSD_PER_CALL", "DISCOVERY_EVALUATED"):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert settings.rag_enabled and settings.rag_evaluated and settings.discovery_evaluated


def test_retrieval_stays_off_by_default_until_a_store_and_corpus_are_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (*RAG_ENV, "RAG_SEARCH_MICROUSD_PER_CALL", "DISCOVERY_EVALUATED"):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert not settings.rag_configured
    assert not settings.discovery_available
    assert not settings.explanation_available


def test_corpus_version_is_read_from_the_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [], "corpus_version": CORPUS_VERSION}))

    assert read_corpus_version(manifest) == CORPUS_VERSION


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(None, id="missing"),
        pytest.param("{not json", id="invalid-json"),
        pytest.param("[]", id="not-an-object"),
        pytest.param('{"corpus_version": ""}', id="empty-version"),
        pytest.param('{"corpus_version": 7}', id="number-version"),
    ],
)
def test_unusable_manifest_has_no_corpus_version(tmp_path: Path, content: str | None) -> None:
    manifest = tmp_path / "manifest.json"
    if content is not None:
        manifest.write_text(content)

    assert read_corpus_version(manifest) is None
