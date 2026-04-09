# AGENTS.md - better-telegram-mcp

**Generated:** 2026-04-08 19:34:05 UTC
**Commit:** 1b150fc
**Branch:** main

Telegram MCP Server. Python 3.13, uv, src layout. Dual-mode: Bot API (httpx) + MTProto (Telethon).

## Build / Lint / Test Commands

```bash
uv sync --group dev                # Install dependencies
uv build                           # Build package (hatchling)
uv run ruff check .                # Lint
uv run ruff format --check .       # Format check
uv run ruff format .               # Format fix
uv run ruff check --fix .          # Lint fix
uv run ty check                    # Type check (Astral ty)
uv run pytest                      # Run all tests (integration excluded by default)
uv run pytest -m integration       # Run integration tests only
uv run better-telegram-mcp         # Run server (stdio)
uv run better-telegram-mcp auth    # Authenticate Telegram user account

# Run a single test file
uv run pytest tests/test_config.py

# Run a single test function
uv run pytest tests/test_config.py::test_function_name -v

# Mise shortcuts
mise run setup     # Full dev environment setup
mise run lint      # ruff check + ruff format --check + ty check
mise run test      # pytest
mise run fix       # ruff check --fix --unsafe-fixes + ruff format
mise run dev       # uv run better-telegram-mcp
```

### Pytest Configuration

- `asyncio_mode = "auto"` -- no `@pytest.mark.asyncio` needed
- Default timeout: 30 seconds per test
- Integration tests excluded by default (`-m 'not integration'`)
- Test files: `test_*.py` in `tests/` directory

## Code Style

### Formatting (Ruff)

- **Line length**: 88 (E501 ignored -- long lines allowed)
- **Quotes**: Double quotes
- **Indent**: 4 spaces (Python), 2 spaces (JSON/YAML/TOML)
- **Line endings**: LF
- **Target**: Python 3.13

### Ruff Rules

`select = ["E", "F", "W", "I", "UP", "B", "C4"]`, `ignore = ["E501"]`

- `I` = isort, `UP` = pyupgrade, `B` = bugbear, `C4` = comprehensions

### Type Checker (ty)

Lenient: `unresolved-import`, `unresolved-attribute`, `possibly-unresolved-reference`, `invalid-return-type`, `invalid-argument-type`, `not-iterable`, `invalid-assignment` all `"ignore"`.

### Import Ordering (isort via Ruff)

1. Standard library (`import asyncio`, `import json`, `import os`)
2. Third-party (`from loguru import logger`, `from mcp.server.fastmcp import FastMCP`)
3. Local (`from better_telegram_mcp.config import Settings`)

Lazy imports inside functions for heavy deps and to avoid circular deps.

```python
import asyncio
import json
from pathlib import Path

from loguru import logger
from mcp.server.fastmcp import Context, FastMCP

from better_telegram_mcp.config import Settings
from better_telegram_mcp.backends.base import TelegramBackend
```

### Type Hints

- Full type hints on all signatures: parameters and return types
- Modern syntax: `str | None`, `list[float]`, `dict[str, object]`
- `from __future__ import annotations` used in some files
- `py.typed` marker file present

### Naming Conventions

| Element            | Convention       | Example                              |
|--------------------|------------------|--------------------------------------|
| Functions/methods  | snake_case       | `send_message`, `_detect_mode`       |
| Private            | Leading `_`      | `_bot`, `_client`, `_ensure_auth`    |
| Classes            | PascalCase       | `Settings`, `BotBackend`, `UserBackend` |
| Constants          | UPPER_SNAKE_CASE | `_MAX_MESSAGE_LENGTH`, `_TIMEOUT`    |
| Modules            | snake_case       | `bot_backend.py`, `user_backend.py`  |

### Error Handling

- MCP tools return error strings: `return "Error: query is required..."` (not exceptions)
- try/except with `logger.debug()` / `logger.warning()` for non-fatal failures
- `match action:` for tool action dispatch
- `asyncio.to_thread()` for wrapping sync operations

### File Organization

```
src/better_telegram_mcp/
  __init__.py, __main__.py    # Package + entry
  config.py                   # Pydantic Settings (env prefix TELEGRAM_)
  server.py                   # FastMCP server with lifespan
  cli.py                      # Auth CLI (terminal OTP input)
  backends/
    base.py                   # TelegramBackend ABC
    bot_backend.py            # httpx -> Telegram Bot API
    user_backend.py           # Telethon MTProto client
  tools/                      # 6 mega-tools (action dispatch)
    messages.py               # send, edit, delete, forward, pin, search
    chats.py                  # info, create, join, leave, settings
    media.py                  # send photo/file/voice/video, download
    contacts.py               # list, search, add, block
    config_tool.py            # auth, send_code, status
    help.py                   # documentation lookup
  docs/                       # Tool documentation markdown
tests/                        # Test files mirror source modules
```

### Documentation

- Module-level docstrings on every file
- Google-style docstrings with `Args:`/`Returns:` sections
- Section separators: `# ---------------------------------------------------------------------------`

### Commits

Conventional Commits: `type(scope): message`. Automated semantic release.

### Pre-commit Hooks

1. Ruff lint (`--fix --target-version=py313`) + format
2. ty type check
3. pytest (`--timeout=30 --tb=short -q`)

## Architecture

- **Dual mode**: `Settings._detect_mode()` auto-selects bot/user based on env vars
- **Backend ABC**: `TelegramBackend` defines interface; `BotBackend` (httpx) and `UserBackend` (Telethon) implement it
- **Mega-tool pattern**: 6 tools x N actions = full API coverage with minimal tool registration overhead
- **Session persistence**: `~/.better-telegram-mcp/<name>.session` for Telethon (MTProto)
- **Auth flow**: OTP sent to Telegram app -> terminal input or `config(action='auth', code='...')` for headless

## TODO / Backlog

- [ ] **Glama display name**: Cannot set programmatically. Update manually via Glama admin page.
