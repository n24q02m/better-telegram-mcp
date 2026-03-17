# CLAUDE.md - better-telegram-mcp

MCP Server cho Telegram. Python 3.13, uv, hatchling, src layout.
Dual-mode: Bot API (httpx) + MTProto (Telethon). 6 mega-tools voi action dispatch.

## Commands

```bash
uv sync --group dev          # Setup
uv run ruff check .          # Lint
uv run ruff format --check . # Format check
uv run ty check              # Type check
uv run pytest                # Test (integration excluded)
uv run ruff check --fix . && uv run ruff format .  # Fix
```

## Cau truc thu muc

```
src/better_telegram_mcp/
  config.py            # Pydantic Settings, env prefix TELEGRAM_
  server.py            # FastMCP server + lifespan + auth web server integration
  auth_server.py       # Starlette web UI for OTP auth (localhost, auto-shutdown)
  backends/            # TelegramBackend ABC -> BotBackend (httpx), UserBackend (Telethon)
  backends/security.py # Input validation: validate_url, validate_file_path, validate_output_dir
  tools/               # 6 mega-tools: messages, chats, media, contacts, config_tool, help
  docs/                # Tool documentation markdown
tests/                 # Mirror source modules
```

## Env vars

Prefix `TELEGRAM_`:
- `TELEGRAM_BOT_TOKEN` -- bot mode
- `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` -- user mode (uu tien hon bot)
- `TELEGRAM_PHONE` -- phone voi country code (VD: `+84912345678`)
- `TELEGRAM_SESSION_NAME` -- ten session file (default: `default`)
- `TELEGRAM_DATA_DIR` -- thu muc data (default: `~/.better-telegram-mcp`)

NO `TELEGRAM_PASSWORD` -- 2FA password nhap qua web UI hoac curl, KHONG luu trong env/config.

## Auth flow

- User mode chua auth -> start Starlette web server tren localhost:random_port
- Browser tu dong mo. Headless: curl POST /send-code + POST /verify
- Auth xong -> web server tu tat -> MCP tools active ngay (khong can restart)
- Session persist tai `~/.better-telegram-mcp/<name>.session`, permission 600

## Luu y

- Mode detection: `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` set -> user mode. Khong co -> bot mode.
- MCP tools tra ve error string, khong raise exception. safe_error() sanitize exceptions.
- `match action:` pattern cho tool action dispatch.
- Coverage fail_under: 95%. Pre-commit: ruff lint + format, ty check, pytest.
- Security: validate_url (SSRF), validate_file_path (traversal), validate_output_dir (write)
- Infisical project: `29457d18-fd82-4942-9330-7da7982e6b1d`
