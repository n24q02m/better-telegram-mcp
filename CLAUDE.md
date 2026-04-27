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
