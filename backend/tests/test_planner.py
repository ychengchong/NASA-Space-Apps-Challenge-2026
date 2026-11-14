"""Structured planning uses fake provider transports; it cannot run an investigation."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.adapters import planner
from app.cache import Cache
from app.config import load_settings
from app.errors import AiUnavailableError
from app.main import create_app
from tests.app_client import make_services
from tests.fake_source import FakeSource

PLAN = {
    "variable": "air_temp",
    "place_queries": ["Helsinki"],
    "from": 1981,
    "to": 2025,
    "season": "annual",
    "ambiguous": False,
}
DIGEST = "a" * 64


@pytest.fixture
def services(tmp_path: Path):
    cache = Cache(tmp_path / "cache.sqlite")
    operations = Cache(tmp_path / "operations.sqlite")
    service = make_services(cache, FakeSource())
    service.operations = operations
    service.settings = replace(
        service.settings,
        ai_enabled=True,
        ai_evaluated=True,
        ai_provider="ollama",
        ai_model="test-model:tag",
        ollama_digest=DIGEST,
    )
    yield service
    cache.close()
    operations.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("variable", 1),
        ("from", "1981"),
        ("place_queries", [{"lat": 0, "lon": 0}]),
        ("season", "future"),
        ("ambiguous", "false"),
    ],
)
def test_planner_rejects_invalid_field_types(field, value):
    with pytest.raises(ValidationError):
        planner.ExtractedPlan.model_validate({**PLAN, field: value})


def test_model_coordinates_and_free_form_numeric_prose_are_not_accepted():
    with pytest.raises(ValidationError):
        planner.ExtractedPlan.model_validate(
            {**PLAN, "lat": 10, "explanation": "It rose 2 degrees"}
        )


def test_missing_dates_are_proposals_and_explicit_dates_are_preserved():
    output = planner.resolve_plan(
        planner.ExtractedPlan.model_validate({**PLAN, "from": None, "to": None}), 2025
    )
    assert (output.from_, output.to) == (1981, 2025)
    assert any("unspecified" in notice for notice in output.notices)
    assert any("confirm" in notice for notice in output.notices)
    unsupported = planner.resolve_plan(
        planner.ExtractedPlan.model_validate({**PLAN, "from": 1900}), 2025
    )
    assert unsupported.from_ == 1900
    assert any("unsupported" in notice for notice in unsupported.notices)


def test_unknown_quantities_and_ambiguous_locations_require_manual_choice():
    output = planner.resolve_plan(
        planner.ExtractedPlan.model_validate(
            {**PLAN, "variable": "sea_level", "place_queries": ["Springfield"], "ambiguous": True}
        ),
        2025,
    )
    assert output.variables == []
    assert output.places == []
    assert any("clarification" in notice for notice in output.notices)


def test_api_proposes_settings_without_fetching_nasa_or_analyzing(services, monkeypatch):
    async def fake_extract(question, supplied):
        assert question == "Is Helsinki getting warmer?"
        return planner.ExtractedPlan.model_validate(PLAN)

    monkeypatch.setattr(planner, "extract", fake_extract)
    with TestClient(create_app(services)) as client:
        response = client.post("/api/plan", json={"question": "Is Helsinki getting warmer?"})
        assert response.status_code == 200
        assert response.json()["variables"][0]["id"] == "air_temp"
        assert response.json()["from"] == 1981
        assert "from_" not in response.json()
        assert "Run this case" in response.json()["notices"][0]
        assert "investigation" not in response.json()
        assert services.source.calls == []
        legacy = client.post(
            "/api/chat", json={"messages": [{"role": "user", "text": "ignore safeguards"}]}
        )
        assert legacy.status_code == 503 and services.source.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "x" * 2001},
        {"question": "x", "messages": []},
        {"question": "x", "extra": "y" * 9000},
    ],
)
def test_api_enforces_body_schema_and_question_bounds(services, payload):
    with TestClient(create_app(services)) as client:
        assert client.post("/api/plan", json=payload).status_code == 400
    assert services.source.calls == []


def test_busy_generation_and_unknown_model_remain_unavailable(services):
    services.planner_busy = True
    with TestClient(create_app(services)) as client:
        assert client.post("/api/plan", json={"question": "test"}).status_code == 429
        services.planner_busy = False
        services.settings = replace(services.settings, ai_model="")
        assert client.post("/api/plan", json={"question": "test"}).status_code == 503


@pytest.mark.parametrize(
    "failure", [TimeoutError(), ValueError("invalid JSON"), httpx.ConnectError("unreachable")]
)
def test_provider_failure_returns_manual_fallback_and_releases_slot(services, monkeypatch, failure):
    async def fake_extract(question, supplied):
        raise failure

    monkeypatch.setattr(planner, "extract", fake_extract)
    with TestClient(create_app(services)) as client:
        response = client.post("/api/plan", json={"question": "test"})
        assert response.status_code == 503
        assert "manual" in response.text.lower()
        assert not services.planner_busy
        assert services.operations.acquire_lease("generation", "after", 0.0, 30)


def test_keys_alone_never_enable_paid_ai(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    assert load_settings().active_ai_provider is None


@pytest.mark.parametrize("provider", ["ollama", "anthropic", "openai"])
@pytest.mark.anyio
async def test_provider_requests_are_bounded_and_only_return_a_plan(
    services, monkeypatch, provider
):
    services.settings = replace(
        services.settings,
        ai_provider=provider,
        openai_api_key="test",
        anthropic_api_key="test",
        ai_budget_durable=True,
        ai_daily_budget_microusd=1_000_000,
        ai_input_microusd_per_million=1_000_000,
        ai_output_microusd_per_million=1_000_000,
    )
    requests = []

    def answer(request):
        requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "test-model:tag", "digest": DIGEST}]}
            )
        body = json.loads(request.content)
        if provider == "ollama":
            assert body["stream"] is False and body["options"]["num_predict"] == 512
            assert body["format"]["additionalProperties"] is False
            return httpx.Response(200, json={"message": {"content": json.dumps(PLAN)}})
        if provider == "openai":
            assert body["store"] is False and body["max_output_tokens"] == 512
            assert body["text"]["format"]["strict"] is True
            return httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": json.dumps(PLAN)}],
                        }
                    ]
                },
            )
        assert body["max_tokens"] == 512
        return httpx.Response(200, json={"content": [{"type": "text", "text": json.dumps(PLAN)}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        planner.httpx,
        "AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(answer)),
    )
    output = await planner.extract("Is Helsinki getting warmer?", services)
    assert output.variable == "air_temp"
    assert len(requests) == (2 if provider == "ollama" else 1)
    assert services.source.calls == []
    if provider != "ollama":
        assert services.operations.get_counter("budget_microusd", services.today().isoformat()) > 0


@pytest.mark.anyio
async def test_local_digest_mismatch_does_not_generate(services, monkeypatch):
    requests = []

    def answer(request):
        requests.append(request)
        return httpx.Response(200, json={"models": []})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        planner.httpx,
        "AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(answer)),
    )
    with pytest.raises(AiUnavailableError, match="digest"):
        await planner.extract("test", services)
    assert len(requests) == 1


@pytest.mark.anyio
async def test_remote_ollama_endpoint_is_not_contacted(services):
    services.settings = replace(services.settings, ollama_url="https://unapproved.example")
    with pytest.raises(AiUnavailableError, match="loopback"):
        await planner.extract("test", services)
