import logging
import re
import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import NoReturn

import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Scope

from app.adapters import chat, rest
from app.cache import Cache
from app.config import get_settings
from app.main import create_app
from app.models import SearchVariablesInput
from app.services import Services
from app.sources.power import PowerClient
from tests.app_client import (
    ASSET_JS,
    ASSET_PATH,
    INDEX_HTML,
    TODAY,
    make_services,
    write_web_app,
)
from tests.fake_source import FakeSource, line, monthly_from_yearly

HELSINKI_CASE = "v=air_temp&p=60.17,24.94&label=Helsinki&from=1981&to=2025&s=annual"
RISING = monthly_from_yearly(line(0.05))
REQUEST_LOGGER = "app.main"
# The status the request log gives a request whose client left before the answer.
CLIENT_CLOSED_REQUEST = 499
# Longer than the 255-byte limit on one file name in macOS and Linux.
TOO_LONG_NAME = "a" * 300


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[Cache]:
    cache = Cache(tmp_path / "cache.sqlite")
    yield cache
    cache.close()


@pytest.fixture
def services(cache: Cache) -> Services:
    return make_services(cache, FakeSource(RISING))


@pytest.fixture
def web_dir(tmp_path: Path) -> Path:
    return write_web_app(tmp_path / "dist")


@pytest.fixture
def client(services: Services, web_dir: Path) -> TestClient:
    return TestClient(create_app(services, static_dir=web_dir))


@pytest.fixture(params=[True, False], ids=["with_web_app", "without_web_app"])
def either_client(request: pytest.FixtureRequest, services: Services, tmp_path: Path) -> TestClient:
    """A client with the built web app, then one without: the service paths answer the same."""
    static_dir = write_web_app(tmp_path / "dist") if request.param else tmp_path / "missing"
    return TestClient(create_app(services, static_dir=static_dir))


def limited_app(cache: Cache, web_dir: Path, limit_per_minute: int) -> TestClient:
    services = make_services(cache, FakeSource(RISING), rate_limit_per_minute=limit_per_minute)
    return TestClient(create_app(services, static_dir=web_dir))


# /healthz


def test_healthz_answers_ok(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# The web app


def test_web_app_files_are_served(client: TestClient) -> None:
    response = client.get(f"/{ASSET_PATH}")

    assert response.status_code == 200
    assert response.text == ASSET_JS


@pytest.mark.parametrize(
    "path",
    [
        "/",
        f"/case?{HELSINKI_CASE}",
        "/map?v=air_temp&box=55,20,65,30&s=annual",
        "/about/team",
        f"/{TOO_LONG_NAME}",
        f"/assets/{TOO_LONG_NAME}.js",
    ],
)
def test_page_paths_get_the_web_app_so_a_link_survives_a_reload(
    client: TestClient, path: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX_HTML


@pytest.mark.parametrize("path", ["/api/nope", "/api", "/healthz/extra"])
def test_service_paths_never_get_the_web_app(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_on_the_chat_path_is_a_wrong_method_with_or_without_the_web_app(
    either_client: TestClient,
) -> None:
    response = either_client.get("/api/chat")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "bad_request"
    assert response.headers["allow"] == "POST"


@pytest.mark.parametrize("path", ["/api/nope", "/api", "/healthz/extra"])
def test_post_to_an_unknown_service_path_is_not_found_with_or_without_the_web_app(
    either_client: TestClient, path: str
) -> None:
    response = either_client.post(path)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_without_a_built_web_app_a_page_path_is_a_json_not_found(
    services: Services, tmp_path: Path
) -> None:
    client = TestClient(create_app(services, static_dir=tmp_path / "missing"))

    response = client.get(f"/case?{HELSINKI_CASE}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("path", ["/..%2fsecret.txt", "/%2e%2e/secret.txt"])
def test_files_outside_the_web_app_are_not_served(
    client: TestClient, web_dir: Path, path: str
) -> None:
    (web_dir.parent / "secret.txt").write_text("SECRET", encoding="utf-8")

    response = client.get(path)

    assert "SECRET" not in response.text


# The chat endpoint (spec 10)


def test_chat_is_mounted_and_answers_ai_unavailable_when_the_ai_is_off(
    services: Services, web_dir: Path
) -> None:
    ai_off = replace(services, settings=replace(services.settings, ai_enabled=False))
    client = TestClient(create_app(ai_off, static_dir=web_dir))

    response = client.post(
        "/api/chat", json={"messages": [{"role": "user", "text": "Is Nairobi getting warmer?"}]}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"


# Rate limit (spec 11)


def test_requests_over_the_limit_are_rate_limited(cache: Cache, web_dir: Path) -> None:
    client = limited_app(cache, web_dir, limit_per_minute=2)

    statuses = [client.get("/api/variables").status_code for _ in range(3)]

    assert statuses == [200, 200, 429]
    assert client.get("/api/variables").json()["error"]["code"] == "rate_limited"


def test_rate_limit_counts_each_address_on_its_own(cache: Cache, web_dir: Path) -> None:
    services = make_services(cache, FakeSource(RISING), rate_limit_per_minute=1)
    app = create_app(services, static_dir=web_dir)
    first = TestClient(app, client=("192.0.2.1", 50000))
    second = TestClient(app, client=("192.0.2.2", 50000))

    assert first.get("/api/variables").status_code == 200
    assert first.get("/api/variables").status_code == 429
    assert second.get("/api/variables").status_code == 200


def test_rate_limit_covers_mcp(cache: Cache, web_dir: Path) -> None:
    client = limited_app(cache, web_dir, limit_per_minute=1)
    client.get("/api/variables")

    assert client.get("/mcp").status_code == 429


@pytest.mark.parametrize("path", ["/healthz", "/case", f"/{ASSET_PATH}", "/api/chat"])
def test_rate_limit_leaves_out_health_web_app_and_chat(
    cache: Cache, web_dir: Path, path: str
) -> None:
    client = limited_app(cache, web_dir, limit_per_minute=1)
    client.get("/api/variables")

    assert client.get(path).status_code != 429


# Logging (spec 11; AGENTS 7: the path, status and duration only)


def test_request_log_holds_method_path_status_and_duration_only(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    client.get(f"/api/case?{HELSINKI_CASE}")

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1
    assert re.fullmatch(r"GET /api/case 200 \d+ ms", messages[0])


def test_request_log_escapes_line_breaks_in_the_path(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    client.get("/api/nope%0AGET%20/forged%20200%201%20ms")

    assert "\n" not in caplog.records[0].getMessage()


def test_uvicorn_access_log_is_off(client: TestClient) -> None:
    assert logging.getLogger("uvicorn.access").disabled


def test_unexpected_error_is_logged_without_request_details(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken_search(inp: SearchVariablesInput) -> NoReturn:
        raise RuntimeError("broken catalogue")

    monkeypatch.setattr(rest, "search_variables", broken_search)
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    client.get("/api/variables?query=secret+words")

    errors = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(errors) == 1
    assert errors[0].exc_info is not None
    assert errors[0].exc_info[1] is not None
    assert str(errors[0].exc_info[1]) == "broken catalogue"
    assert "/api/variables" not in errors[0].getMessage()
    assert "secret" not in caplog.text


def chat_request_scope() -> Scope:
    """The ASGI scope of a POST to /api/chat, as uvicorn passes it."""
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("192.0.2.1", 50000),
        "root_path": "",
        "path": "/api/chat",
        "raw_path": b"/api/chat",
        "query_string": b"",
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
    }


async def send_chat_from_a_client_that_disconnects(
    services: Services, web_dir: Path
) -> list[Message]:
    """POST /api/chat with the AI on, from a client that leaves before sending its body.

    Returns the messages the app sent back.
    """
    ai_on = replace(
        services, settings=replace(services.settings, ai_enabled=True, anthropic_api_key="test")
    )
    app = create_app(ai_on, static_dir=web_dir)
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    try:
        await app(chat_request_scope(), receive, send)
    finally:
        await chat.close_chat_backend(app.state.chat_backend)
    return sent


@pytest.mark.anyio
async def test_client_that_disconnects_mid_request_is_not_logged_as_an_error(
    services: Services, web_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    await send_chat_from_a_client_that_disconnects(services, web_dir)

    assert [record for record in caplog.records if record.levelno >= logging.ERROR] == []


@pytest.mark.anyio
async def test_client_that_disconnects_mid_request_gets_no_answer(
    services: Services, web_dir: Path
) -> None:
    assert await send_chat_from_a_client_that_disconnects(services, web_dir) == []


@pytest.mark.anyio
async def test_request_log_records_a_client_that_disconnects_mid_request_as_closed(
    services: Services, web_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    await send_chat_from_a_client_that_disconnects(services, web_dir)

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1
    assert re.fullmatch(rf"POST /api/chat {CLIENT_CLOSED_REQUEST} \d+ ms", messages[0])


# Lifespan


@pytest.fixture
def fresh_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Settings read anew from an environment whose cache file is in a temporary folder."""
    cache_path = tmp_path / "env_cache.sqlite"
    monkeypatch.setenv("CACHE_PATH", str(cache_path))
    get_settings.cache_clear()
    yield cache_path
    get_settings.cache_clear()


def test_app_without_services_builds_them_at_startup_and_closes_them_at_shutdown(
    fresh_settings: Path, web_dir: Path
) -> None:
    app = create_app(static_dir=web_dir)

    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        services: Services = app.state.services
        assert services.settings.cache_path == fresh_settings
        assert isinstance(services.source, PowerClient)

    with pytest.raises(sqlite3.ProgrammingError):
        services.cache.get_counter("ai_turns", TODAY.isoformat())
