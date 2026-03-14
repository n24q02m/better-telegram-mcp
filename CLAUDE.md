# better-telegram-mcp

MCP server cho Telegram. Dual-mode: Bot API (httpx) + MTProto (Telethon).

## Commands

- `uv run pytest` — Run tests (skip integration)
- `uv run pytest -m integration` — Run integration tests (need Telegram credentials)
- `uv run ruff check src/ tests/` — Lint
- `uv run ty check src/` — Type check
- `uv run better-telegram-mcp` — Run server (stdio)
- `uv run better-telegram-mcp auth` — Interactive Telethon auth

## Architecture

- `backends/base.py` — TelegramBackend ABC
- `backends/bot_backend.py` — httpx → Telegram Bot API REST
- `backends/user_backend.py` — Telethon MTProto
- `tools/*.py` — Mega-tools (action dispatch pattern)
- `config.py` — Pydantic settings from env vars
- Mode auto-detect: TELEGRAM_API_ID → user, TELEGRAM_BOT_TOKEN → bot

## Conventions

- Conventional Commits
- Tests >= 95% coverage
- Vietnamese docs/comments where appropriate
