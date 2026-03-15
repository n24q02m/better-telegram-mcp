FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-editable

COPY src/ src/
RUN uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/n24q02m/better-telegram-mcp"
LABEL io.modelcontextprotocol.server.name="io.github.n24q02m/better-telegram-mcp"

RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

VOLUME /data
ENV TELEGRAM_DATA_DIR=/data

ENTRYPOINT ["python", "-m", "better_telegram_mcp"]
