# CLAUDE.md - better-telegram-mcp

MCP Server cho Telegram. Python 3.13, uv, hatchling, src layout.
Dual-mode: Bot API (httpx) + MTProto (Telethon). 6 tools: message, chat, media, contact, config, help.

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
  relay_setup.py       # Zero-config relay: create session, poll for config
  relay_schema.py      # Relay form schema (bot mode + user mode fields)
  tools/               # messages, chats, media, contacts, config_tool, help
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
- `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` -- user mode (built-in defaults, override optional)
- `TELEGRAM_PHONE` -- phone (required for auth web UI)
- `TELEGRAM_AUTH_URL` -- `local` | remote URL (default: remote)
- `TELEGRAM_SESSION_NAME`, `TELEGRAM_DATA_DIR` -- optional

NO `TELEGRAM_PASSWORD` -- 2FA nhap qua web UI, KHONG luu env.

## Release & Deploy

- Conventional Commits. Tag format: `v{version}`
- CD: PSR v10 -> PyPI (uv publish) -> Docker multi-arch (amd64 + arm64) -> MCP Registry
- Docker images: `n24q02m/better-telegram-mcp`

## Pre-commit hooks

1. Ruff lint (`--fix`) + format
2. ty type check
3. pytest (`--tb=short -q`)
4. Commit message: enforce Conventional Commits

## Luu y

- Config tool: `status|set|cache_clear` (NO auth/send_code -- web UI only)
- Coverage omit: auth_server.py, auth_client.py (integration test only)
- Security: SSRF, path traversal, error sanitization, rate limiting on relay
- Secrets: skret SSM namespace `/better-telegram-mcp/prod` (region `ap-southeast-1`)

## Known bugs (phat hien 2026-04-18 E2E)

**CRITICAL SECURITY BUG: Bot token leak trong stderr logs**:
- `src/better_telegram_mcp/backends/bot_backend.py:24`: `self._base_url = API_BASE.format(bot_token)` -> httpx.AsyncClient(base_url=...) -> **httpx default INFO logging** print full URL incluing bot token len stderr (vi du: `https://api.telegram.org/bot8739495379:AAF-qAG...ta redacted/sendMessage "HTTP/1.1 200 OK"`)
- Bot token co the bi leak qua: (1) log file, (2) monitoring dashboards, (3) screenshots, (4) error reports
- **Fix required:**
  (a) set logger level cho `httpx` library = WARNING (tat INFO-level HTTP request logs), HOAC
  (b) dung httpx event_hooks de redact token trong URL truoc khi log, HOAC
  (c) pass bot_token qua httpx `params` thay vi URL (khong dang vi Telegram API spec requires URL)
- **Option (a) don gian nhat:** them vao `init-server.ts` / server startup: `logging.getLogger("httpx").setLevel(logging.WARNING)`
- Phat hien 2026-04-18 E2E test: phase 2 tools call dump URL with token in stderr

1. **User mode OTP/2FA flow BROKEN o relay page**:
   - Steps thuc te: submit phone -> relay bao "done" -> server **KHONG** prompt OTP -> session never authorized (`authorized=false`, `pending_auth=true`)
   - Root cause: `src/better_telegram_mcp/relay_schema.py` `RELAY_SCHEMA` chi co flat fields `TELEGRAM_BOT_TOKEN` + `TELEGRAM_PHONE`. KHONG co multi-step cho OTP + 2FA password
   - Per credential_state.py:208: "User-mode OTP/2FA now runs through the local OAuth form + /otp endpoint" -- nghia la browser SHOULD redirect tu relay den local 127.0.0.1:PORT/otp. Nhung browser khong redirect -> user mac ket
   - **Impact:** User mode (MTProto) ho`ang hoan toan. Chi bot mode co the su dung.
   - **Fix required:**
     (a) update RELAY_SCHEMA them multi-step: phone -> submit -> show OTP input -> submit -> if 2FA enabled show password input -> submit, HOAC
     (b) relay page redirect den local 127.0.0.1/otp sau khi phone save, HOAC
     (c) su dung RELAY_SCHEMA_MODES (da co san o line 46) thay vi flat RELAY_SCHEMA

2. **Bot mode**: chua verify end-to-end (phase M E2E 2026-04-18 time-out chua test bot)

3. **Relay "Setup complete" browser UI** (if Python core-py has same bug): chua observe, nhung neu user mode fix xong, can verify browser hien "Setup complete!" sau OTP done
