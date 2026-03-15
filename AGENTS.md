# AGENTS.md - better-telegram-mcp

Telegram MCP Server. Python 3.13, uv, src layout. Dual-mode: Bot API (httpx) + MTProto (Telethon).

## Build / Lint / Test Commands

```bash
uv sync --group dev                # Install dependencies
uv build                           # Build package (hatchling)
uv run ruff check .                # Lint
uv run ruff format --check .       # Format check
uv run ruff format .               # Format fix
uv run ruff check --fix .          # Lint fix
uv run pytest                      # Run all tests (integration excluded by default)
uv run pytest -m integration       # Run integration tests only
uv run better-telegram-mcp         # Run server (stdio)
uv run better-telegram-mcp auth    # Authenticate Telegram user account

# Mise shortcuts
mise run setup     # Full dev environment setup
mise run lint      # ruff check + ruff format --check
mise run test      # pytest
mise run fix       # ruff check --fix + ruff format
mise run dev       # uv run better-telegram-mcp
```

## Architecture

- `src/better_telegram_mcp/backends/base.py` -- TelegramBackend ABC
- `src/better_telegram_mcp/backends/bot_backend.py` -- httpx -> Telegram Bot API
- `src/better_telegram_mcp/backends/user_backend.py` -- Telethon MTProto
- `src/better_telegram_mcp/tools/*.py` -- 6 mega-tools (action dispatch)
- `src/better_telegram_mcp/config.py` -- Pydantic settings from env vars
- `src/better_telegram_mcp/server.py` -- FastMCP server with lifespan

## Conventions

- Conventional Commits
- Python 3.13 only
- ruff for lint+format
- pytest with >= 95% coverage
- python-semantic-release for versioning
