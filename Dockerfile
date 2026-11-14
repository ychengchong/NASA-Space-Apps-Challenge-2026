# Trend Detective as one container (spec 11, "Deployment"). The backend serves the API, /mcp
# and the built web app at one URL.
#
# From the repository root:
#   docker build -t trend-detective .
#   docker run --rm -p 8000:8000 --env-file .env trend-detective

# Stage 1: build the web app.
FROM node:22.23.5-trixie-slim AS frontend
WORKDIR /app/frontend
# The manifest and lock file come first, so the dependency layer is reused until they change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: install the backend's pinned runtime dependencies from uv.lock, without the dev group.
FROM python:3.12.16-slim-trixie AS backend-deps
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /bin/uv
# Use the image's own Python, and compile bytecode now, because the app user cannot write it.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-cache

# Stage 3: the running service. Same base image as stage 2, so the copied virtual environment
# finds its Python at the same path.
FROM python:3.12.16-slim-trixie
# Matplotlib needs a writable folder for its font cache, and the app user has no home folder.
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib
RUN useradd --system --user-group --no-create-home --home-dir /nonexistent \
    --shell /usr/sbin/nologin app
WORKDIR /app/backend
COPY --from=backend-deps /app/backend/.venv ./.venv
COPY backend/app ./app
# The app user owns data/, because SQLite writes the cache and its journal file there.
COPY --chown=app:app backend/data ./data
# app/config.py serves the web app from <backend parent>/frontend/dist.
COPY --from=frontend /app/frontend/dist /app/frontend/dist
USER app
EXPOSE 8000
# --proxy-headers takes each visitor's address from X-Forwarded-For, so each visitor has their
# own rate limit, but only on requests from an address in FORWARDED_ALLOW_IPS, which uvicorn
# reads itself (spec 11, "Deployment"). The default trusts loopback alone, so a client cannot
# choose its own address; on deploy, set it to the address range of the platform's proxy.
ENV FORWARDED_ALLOW_IPS=127.0.0.1
# Shell form, so the host's PORT is expanded; exec makes uvicorn the process that gets the stop
# signal. The access log is off because it records client addresses and query strings (spec 11,
# "Security and privacy").
CMD exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers \
    --no-access-log
