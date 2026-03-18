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

## Cau truc

```
src/better_telegram_mcp/
  config.py            # Pydantic Settings, env prefix TELEGRAM_
  server.py            # FastMCP + lifespan + auth mode switching
  auth_server.py       # Local mode: Starlette web UI on localhost
  auth_client.py       # Remote mode: httpx client polls relay server
  backends/            # TelegramBackend ABC -> BotBackend (httpx), UserBackend (Telethon)
  backends/security.py # validate_url, validate_file_path, validate_output_dir
  tools/               # messages, chats, media, contacts, config_tool, help
auth-relay/            # Remote auth relay server (deploy Docker on OCI VM)
```

## Auth flow

Dual-mode auth (TELEGRAM_AUTH_URL):
- `local` -> auth_server.py (Starlette on localhost, browser moi tu dong)
- `https://...` -> auth_client.py (poll remote relay, browser bat ky dau)
- Default: `https://better-telegram-mcp.n24q02m.com`

Auth xong -> _pending_auth=False -> tools active ngay (khong can restart).
Session persist: `~/.better-telegram-mcp/<name>.session`, permission 600.

## Env vars

- `TELEGRAM_BOT_TOKEN` -- bot mode
- `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` -- user mode
- `TELEGRAM_PHONE` -- phone (required for auth web UI)
- `TELEGRAM_AUTH_URL` -- `local` | remote URL (default: remote)
- `TELEGRAM_SESSION_NAME`, `TELEGRAM_DATA_DIR` -- optional

NO `TELEGRAM_PASSWORD` -- 2FA nhap qua web UI, KHONG luu env.

## Luu y

- Config tool: `status|set|cache_clear` (NO auth/send_code -- web UI only)
- Coverage omit: auth_server.py, auth_client.py (integration test only)
- Security: SSRF, path traversal, error sanitization, rate limiting on relay
- Infisical project: `29457d18-fd82-4942-9330-7da7982e6b1d`
