"""Builds the FastAPI app: the adapters, the error shape, the limits, the log and the web app.

Run it from backend/ with `uv run uvicorn app.main:app --reload`.
"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from starlette.datastructures import State
from starlette.requests import ClientDisconnect
from starlette.routing import Match
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.adapters import chat, rest
from app.adapters import mcp_server as mcp_adapter
from app.config import FRONTEND_DIST_DIR, Settings, get_settings
from app.errors import RateLimitedError
from app.ratelimit import RateLimiter
from app.services import Services, build_services, close_services

APP_TITLE = "Trend Detective"

API_PATH = "/api"
CHAT_PATH = chat.CHAT_PATH
MCP_PATH = mcp_adapter.MCP_PATH
HEALTHZ_PATH = "/healthz"
# The first path segments the service answers itself; the web app never serves them.
SERVICE_SEGMENTS = frozenset({"api", "mcp", "healthz"})
INDEX_FILE = "index.html"

MS_PER_SECOND = 1000
# The status logged for a request whose client left before the answer: nginx's "client closed
# request". It is never sent, because no one is left to receive it.
CLIENT_CLOSED_REQUEST = 499
RATE_LIMITED_MESSAGE = "Too many requests from this address. Please wait a minute and try again."
# The key for a request whose client address the server did not report.
UNKNOWN_CLIENT = "unknown"
# The MCP SDK's logger for the Host and Origin checks of /mcp.
MCP_SECURITY_LOGGER = "mcp.server.transport_security"

logger = logging.getLogger(__name__)


def create_app(services: Services | None = None, static_dir: Path | None = None) -> FastAPI:
    """The whole service as one ASGI app.

    Without `services`, the app builds them from the environment when it starts and closes them
    when it stops. `static_dir` holds the built web app and defaults to `frontend/dist`; when it
    has no index.html, the app serves the API alone.
    """
    _configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            if services is None:
                # Built here, inside the running loop, because the POWER client is bound to it.
                built = build_services(get_settings())
                stack.push_async_callback(close_services, built)
                _use_services(app, built)
            # The stack unwinds in reverse: MCP stops first, then the AI client, then services.
            stack.push_async_callback(chat.close_chat_backend, app.state.chat_backend)
            # Spec 9: without the session manager running, the first MCP request fails.
            await stack.enter_async_context(app.state.mcp_server.session_manager.run())
            yield

    # No /docs or /openapi.json: those paths belong to the web app, and Swagger UI would load
    # its files from a CDN, a destination the app does not otherwise talk to.
    app = FastAPI(
        title=APP_TITLE, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )
    if services is not None:
        _use_services(app, services)

    rest.add_error_handlers(app)
    # The last middleware added is the outermost, so the request log also records the 429 and
    # 500 answers of the other two.
    app.add_middleware(InternalErrorMiddleware)
    app.add_middleware(RateLimitMiddleware, state=app.state)
    app.add_middleware(RequestLogMiddleware)

    app.include_router(rest.router)
    app.include_router(chat.router)
    app.add_api_route(HEALTHZ_PATH, healthz, methods=["GET"])
    _add_mcp(app, services.settings if services is not None else get_settings())
    # The web app's catch-all route stays last, so it never shadows another GET route.
    _add_web_app(app, static_dir if static_dir is not None else FRONTEND_DIST_DIR)
    return app


def _use_services(app: FastAPI, services: Services) -> None:
    app.state.services = services
    app.state.rate_limiter = RateLimiter(services.settings.rate_limit_per_minute)
    app.state.chat_backend = chat.create_chat_backend(services)


def _add_mcp(app: FastAPI, settings: Settings) -> None:
    """Serve the MCP server at /mcp (spec 9). The lifespan runs its session manager."""

    def app_services() -> Services:
        services: Services = app.state.services
        return services

    server = mcp_adapter.create_mcp_server(app_services)
    app.state.mcp_server = server
    # The SDK app's routes, which start with the refusal of every method but POST, join this
    # app's router rather than being mounted: a mount at /mcp would answer POST /mcp with a
    # redirect to /mcp/.
    app.router.routes.extend(mcp_adapter.create_http_app(server, settings.public_base_url).routes)


async def healthz() -> dict[str, str]:
    """Liveness check (spec 10)."""
    return {"status": "ok"}


# Logging (spec 11, "Security and privacy")


def _configure_logging() -> None:
    # uvicorn's access log records client addresses and query strings, so it is off. This
    # app's own request log records only the method, path, status and duration.
    logging.getLogger("uvicorn.access").disabled = True
    # The MCP SDK logs the Host or Origin header of each request it refuses. The request log
    # already records the refusal by its status.
    logging.getLogger(MCP_SECURITY_LOGGER).setLevel(logging.ERROR)
    # Only this module's logger gets a handler: a root handler would also print the HTTP
    # client's log, whose lines hold the coordinates sent to NASA POWER.
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


class RequestLogMiddleware:
    """Logs one line per request: method, path without the query string, status and duration.

    When the client disconnects while the app reads its request, the request ends here, logged
    with CLIENT_CLOSED_REQUEST: that is no failure of the service, and no one is left to answer.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        # The status logged when the app fails before it answers.
        status = HTTPStatus.INTERNAL_SERVER_ERROR.value

        async def send_and_record(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_and_record)
        except ClientDisconnect:
            status = CLIENT_CLOSED_REQUEST
        finally:
            duration_ms = (time.perf_counter() - started) * MS_PER_SECOND
            # quote() escapes line breaks, so a crafted path cannot forge a log line.
            logger.info(
                "%s %s %d %.0f ms", scope["method"], quote(scope["path"]), status, duration_ms
            )


# Limits (spec 11, "Security and privacy")


class RateLimitMiddleware:
    """Answers 429 `rate_limited` once a client address sends too many requests in a minute.

    It covers /api, except /api/chat, which has its own AI limits, and /mcp. The address comes
    from the ASGI scope; behind a proxy, uvicorn's --proxy-headers puts the real one there.
    """

    def __init__(self, app: ASGIApp, state: State) -> None:
        self.app = app
        # The app's state, where the limiter is stored once the services exist.
        self.state = state

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and _is_rate_limited(scope["path"]):
            limiter: RateLimiter = self.state.rate_limiter
            if not limiter.allow(_client_address(scope)):
                response = rest.app_error_response(RateLimitedError(RATE_LIMITED_MESSAGE))
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _is_under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _is_rate_limited(path: str) -> bool:
    if _is_under(path, MCP_PATH):
        return True
    return _is_under(path, API_PATH) and not _is_under(path, CHAT_PATH)


def _client_address(scope: Scope) -> str:
    client = scope.get("client")
    return client[0] if client else UNKNOWN_CLIENT


# Unexpected errors (spec 10, "Errors")


class InternalErrorMiddleware:
    """Turns an unexpected exception into a 500 `internal_error` answer with a plain message.

    The exception is logged with its traceback but without request details, and the client
    never sees it. Once an answer has started, as in a stream, it can no longer be replaced, so
    the exception goes on to the server. A client's disconnect is no error, so it goes on,
    unanswered, to the request log.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response_started = False

        async def send_and_track(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_and_track)
        except ClientDisconnect:
            raise
        except Exception:
            if response_started:
                raise
            logger.exception("Unexpected error while answering a request")
            await rest.internal_error_response()(scope, receive, send)


# The web app (spec 10: any other GET path serves it)


def _add_web_app(app: FastAPI, static_dir: Path) -> None:
    """Serve the built web app at every GET path the service does not answer itself.

    A path that names a file gets that file; any other path gets index.html, so a shared link
    such as /case?... or /map?... survives a reload. Without index.html nothing is added, and
    such paths get the JSON 404.
    """
    root = static_dir.resolve()
    index = root / INDEX_FILE
    if not index.is_file():
        return

    async def web_app(path: str) -> FileResponse:
        file = _web_app_file(root, path) or index
        # index.html names the current build's asset files, so the browser asks for it anew.
        headers = {"Cache-Control": "no-cache"} if file == index else None
        return FileResponse(file, headers=headers)

    # The router's method, because FastAPI's own add_api_route takes no route class.
    app.router.add_api_route(
        "/{path:path}",
        web_app,
        methods=["GET"],
        include_in_schema=False,
        route_class_override=_WebAppRoute,
    )


class _WebAppRoute(APIRoute):
    """The web app's catch-all route, which never matches a path under a service segment.

    Routing leaves those paths out, rather than the handler, so under /api, /mcp and /healthz an
    unknown path gets 404 and a wrong method gets 405 with the right `Allow`, with or without
    the web app (spec 10, "Errors").
    """

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        match, child_scope = super().matches(scope)
        if match is Match.NONE:
            return match, child_scope
        if child_scope["path_params"]["path"].split("/", 1)[0] in SERVICE_SEGMENTS:
            return Match.NONE, {}
        return match, child_scope


def _web_app_file(root: Path, path: str) -> Path | None:
    """The file `path` names inside `root`, or None when it names none or points outside."""
    try:
        candidate = (root / path).resolve()
        found = candidate.is_relative_to(root) and candidate.is_file()
    # ValueError: a null byte in the path. OSError: a name the file system refuses as too long.
    except (OSError, ValueError):
        return None
    return candidate if found else None


app = create_app()
