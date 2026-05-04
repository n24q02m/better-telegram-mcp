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
  credential_state.py  # save_credentials/on_step_submitted callbacks +
                       # _current_sub contextvar (multi-user routing)
  auth/
    telegram_auth_provider.py  # Per-sub Telethon backend lifecycle
    in_memory_session_store.py # bearer/sub -> SessionInfo (RAM only)
    per_user_session_store.py  # SessionInfo dataclass (storage shim)
  backends/            # TelegramBackend ABC -> BotBackend (httpx), UserBackend (Telethon)
  backends/security.py # validate_url, validate_file_path, validate_output_dir
  relay_setup.py       # Shared error sanitization, field constants
  relay_schema.py      # Relay form schema (bot mode + user mode fields)
  credential_form.py   # Custom HTML form (phone -> OTP -> 2FA password)
  transports/
    http.py            # _start_single_user_http + _start_multi_user_http
                       # (both via mcp-core run_http_server)
    credential_store.py# Master-secret resolution helper
  tools/               # messages, chats, media, contacts, config_tool, help
```

## Auth flow

Stdio mode (default): bot-only via `TELEGRAM_BOT_TOKEN` env. User mode is
HTTP-only.

HTTP mode (`--http` / `MCP_TRANSPORT=http`): mcp-core `run_http_server`
serves the local OAuth AS at `/authorize`. The custom credential form
collects bot_token OR phone, posts to `/save`, and chains OTP / 2FA via
`/otp`.

- **Single-user**: writes to `config.enc`, hot-reloads the global Telethon
  backend in `server.py`.
- **Multi-user remote** (`PUBLIC_URL` + `DCR_SERVER_SECRET` set): per-sub
  Telethon backends managed by `TelegramAuthProvider`; the auth_scope
  middleware (`_per_request_sub_scope`) pins the JWT sub + per-user
  backend into contextvars before each MCP tool call.

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

- Config tool: `status|set|cache_clear|setup_*` (auth flow lives in mcp-core HTTP OAuth AS)
- Security: SSRF, path traversal, error sanitization, rate limiting on relay
- Secrets: skret SSM namespace `/better-telegram-mcp/prod` (region `ap-southeast-1`)

## Known bugs

(All 2026-04-18 E2E findings have been resolved. Section retained as a
short audit trail with the fix commit so future investigators do not
re-open closed issues.)

1. **Bot token leak via httpx INFO logs** -- RESOLVED. `server.py:24` sets
   `logging.getLogger("httpx").setLevel(logging.WARNING)` so request URLs
   (which include the bot token) never reach stderr at INFO level.

2. **User mode OTP/2FA multi-step flow** -- RESOLVED. `credential_form.py`
   ships a custom dark-themed form with `showStepInput` JS that handles
   `next_step.type === "otp_required"` + `password_required`. Wired into
   mcp-core's local OAuth AS via `run_local_server(...,
   custom_credential_form_html=render_telegram_credential_form,
   on_step_submitted=on_step_submitted)`. After phone submit, the same
   page re-renders the OTP input, posts to `/otp`, and chains to the 2FA
   password step if Telethon reports it. Recent reinforcements:
   `0560529 fix: follow redirect_url after async OTP/password completion`,
   `eb1993f fix: clear aria-busy on step-input reset to unblock 2FA submit`.

3. **Setup-complete UI redirect** -- RESOLVED via mcp-core
   `feedback_relay_form_must_follow_redirect.md` fix; the form follows
   `redirect_url` instead of showing a static "close tab" page.

## E2E

Driven by `mcp-core/scripts/e2e/` (matrix-locked, 15 configs). Run a single config from this repo via `make e2e` (proxy) or directly:

```
cd ../mcp-core && uv run --project scripts/e2e python -m e2e.driver <config-id>
```

Configs for this repo: `telegram-bot`, `telegram-user`.

``telegram-user`` is t2-interaction (browser-form OTP + 2FA, 600s timeout).

Tier policy:

- **T0** (precommit + CI on PR / main push) - runs without upstream identity. Skret keys not required.
- **T2 non-interaction** (`make e2e-config CONFIG=<id>` locally) - driver pre-fills relay form from skret AWS SSM `/better-telegram-mcp/prod` (`ap-southeast-1`). No user gate.
- **T2 interaction** - driver fills relay form, then prints upstream user-gate URL; user signs in / types OTP at provider. Driver enforces per-flow timeouts (device-code 900s, oauth-redirect 300s, browser-form 600s) and emits `[poll] elapsed=Xs remaining=Ys status=<body>` every 30s. On timeout, container logs + last `setup-status` are saved to `<tmp>/e2e-diag/` BEFORE teardown for post-mortem.

Multi-user remote mode (deployment property; not a separate config) requires `MCP_DCR_SERVER_SECRET` in the same skret namespace - driver refuses to start the container without it when `PUBLIC_URL` is set.

References: `mcp-core/scripts/e2e/matrix.yaml`, `~/.claude/skills/mcp-dev/references/e2e-full-matrix.md` (harness-readiness gate), `~/.claude/skills/mcp-dev/references/secrets-skret.md` (per-server credential layout), `~/.claude/skills/mcp-dev/references/multi-user-pattern.md` (per-JWT-sub isolation).
