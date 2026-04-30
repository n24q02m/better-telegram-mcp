# syntax=docker/dockerfile:1
# Multi-stage build for better-telegram-mcp
# Python 3.13 + httpx (Bot API) + Telethon (MTProto)

# ========================
# Stage 1: Builder
# ========================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first (cached when deps don't change)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application code and install the project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ========================
# Stage 2: Runtime base (shared by stdio + http targets)
# ========================
# Multi-target Dockerfile per spec
# `~/projects/.superpower/mcp-core/specs/2026-04-30-multi-mode-stdio-http-architecture.md`
# section D6. Build stdio: `docker buildx build --target stdio -t <repo>:stdio .`
# Build http:  `docker buildx build --target http  -t <repo>:http .`
# Build latest (= http): `docker buildx build --target http -t <repo>:latest .`
FROM python:3.13-slim-bookworm@sha256:bb73517d48bd32016e15eade0c009b2724ec3a025a9975b5cd9b251d0dcadb33 AS runtime

LABEL org.opencontainers.image.source="https://github.com/n24q02m/better-telegram-mcp"
LABEL io.modelcontextprotocol.server.name="io.github.n24q02m/better-telegram-mcp"

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    TELEGRAM_DATA_DIR=/data \
    HOST=0.0.0.0

# Create non-root user and set permissions
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data /home/appuser

VOLUME /data
USER appuser

# ========================
# Stage 3a: stdio target (default for plugin marketplace & uvx-style usage)
# ========================
FROM runtime AS stdio
ENV MCP_TRANSPORT=stdio
ENTRYPOINT ["python", "-m", "better_telegram_mcp"]

# ========================
# Stage 3b: http target (multi-user remote daemon)
# ========================
FROM runtime AS http
ENV MCP_TRANSPORT=http \
    MCP_PORT=8080
EXPOSE 8080
ENTRYPOINT ["python", "-m", "better_telegram_mcp"]
