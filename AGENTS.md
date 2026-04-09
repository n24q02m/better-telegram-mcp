# AGENTS.md - better-telegram-mcp

**Generated:** 2026-04-09 11:58:55 UTC
**Commit:** 96edca7
**Branch:** relay/shared-http-event-relay

Telegram MCP Server. Python 3.13, `uv`, src layout. Supports stdio plus HTTP transport, with bot/user Telegram backends, relay-assisted setup flows, and bearer-authenticated SSE in multi-user HTTP mode.

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
uv run better-telegram-mcp         # Run server (stdio by default)

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
- Default addopts exclude `integration`, `live`, `full`, and `e2e`
- Test files live in `tests/` as `test_*.py`

## Code Style

### Formatting (Ruff)

- **Line length**: 88 (`E501` ignored)
- **Quotes**: Double quotes
- **Indent**: 4 spaces (Python), 2 spaces (JSON/YAML/TOML)
- **Line endings**: LF
- **Target**: Python 3.13

### Ruff Rules

`select = ["E", "F", "W", "I", "UP", "B", "C4"]`, `ignore = ["E501"]`

- `I` = isort, `UP` = pyupgrade, `B` = bugbear, `C4` = comprehensions

### Type Checker (ty)

Lenient: `unresolved-import`, `unresolved-attribute`, `possibly-unresolved-reference`, `invalid-return-type`, `invalid-argument-type`, `not-iterable`, `invalid-assignment` are ignored.

### Import Ordering

1. Standard library
2. Third-party
3. Local package imports

Lazy imports are used for heavy dependencies and to avoid circular imports.

### Type Hints

- Full type hints on public and internal signatures
- Modern syntax: `str | None`, `list[str]`, `dict[str, object]`
- `from __future__ import annotations` is common
- `py.typed` marker present

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Functions/methods | snake_case | `send_message`, `_detect_mode` |
| Private helpers | Leading `_` | `_current_backend`, `_check_rate_limit` |
| Classes | PascalCase | `Settings`, `TelegramAuthProvider` |
| Constants | UPPER_SNAKE_CASE | `_RATE_LIMIT_AUTH`, `_NONCE_SIZE` |
| Modules | snake_case | `auth_server.py`, `http_multi_user.py` |

### Error Handling

- MCP tools usually return formatted error strings instead of raising user-facing exceptions
- Transport/auth layers raise `ValueError` or `RuntimeError` for invalid flows, then translate at boundaries
- Non-fatal paths log with `logger.debug()` / `logger.warning()`
- `asyncio.to_thread()` is used when sync work must not block async code

## File Organization

```
src/better_telegram_mcp/
  __main__.py                 # Entrypoint; calls server.main()
  server.py                   # FastMCP server, global lifecycle, stdio/single-user runtime
  config.py                   # Settings, mode detection, relay + SSE config
  credential_state.py         # Non-blocking credential/setup state machine
  relay_setup.py              # Relay-assisted setup resolution and OTP/2FA flow
  relay_schema.py             # Relay UI schema for bot vs user setup
  auth_server.py              # Local browser auth page flow
  auth_client.py              # Remote relay polling auth client
  auth/                       # Per-bearer auth/session lifecycle
  backends/                   # Bot/User backend implementations and producers
  events/                     # Shared event envelope + fanout primitives
  tools/                      # MCP tool handlers
  transports/                 # HTTP bootstrap, multi-user app, credential storage
tests/                        # Unit/integration/E2E coverage
docs/                         # User-facing setup and flow documentation
```

## Where To Look

| Task | Location | Notes |
|---|---|---|
| Stdio startup and global backend lifecycle | `src/better_telegram_mcp/server.py` | Root entry for non-HTTP runtime |
| Settings and transport/runtime knobs | `src/better_telegram_mcp/config.py` | Includes relay and unified SSE defaults |
| Relay-assisted setup state machine | `src/better_telegram_mcp/credential_state.py`, `relay_setup.py`, `relay_schema.py` | Root owns this cluster |
| Local vs relay auth UX | `auth_server.py`, `auth_client.py` | Browser page vs remote polling |
| Multi-user bearer auth and runtime ownership | `src/better_telegram_mcp/auth/telegram_auth_provider.py` | See `auth/AGENTS.md` for local rules |
| HTTP bootstrap, `/mcp`, `/events/telegram` | `src/better_telegram_mcp/transports/` | See `transports/AGENTS.md` |
| Telegram delivery backends and polling | `src/better_telegram_mcp/backends/` | See `backends/AGENTS.md` |
| MCP tool action dispatch | `src/better_telegram_mcp/tools/` | See `tools/AGENTS.md` |
| Test fixtures and marker conventions | `tests/` | See `tests/AGENTS.md` |

### Hierarchy Boundaries

- `transports/AGENTS.md` owns HTTP bootstrap, bearer auth wiring, encrypted single-user credential storage, and SSE transport semantics.
- `auth/AGENTS.md` owns per-user session persistence, bearer runtime lifecycle, and Telegram auth provider invariants.
- `events/` is still documented from root plus `transports/AGENTS.md`; do not treat it as an independent user-facing subsystem yet.

## Architecture

- **Runtime split**: `__main__.py` delegates to `server.main()`, which runs stdio by default and coordinates shared lifecycle concerns.
- **Two HTTP modes**: `transports/http.py` chooses between single-user HTTP fallback and multi-user HTTP mode via `_is_multi_user_mode()`.
- **Single-user HTTP fallback**: environment variables win; otherwise encrypted credentials from `CredentialStore`; otherwise relay-assisted setup populates local credentials.
- **Multi-user HTTP mode**: `transports/http_multi_user.py` exposes auth endpoints, bearer-authenticated `/mcp`, `GET /events/telegram`, and per-request backend injection via `_current_backend`.
- **Provider-owned runtimes**: `TelegramAuthProvider` owns per-bearer bot/user backends plus per-bearer SSE fanout hubs; restored sessions must attach sinks after runtime creation.
- **Unified SSE**: one live-only `GET /events/telegram` stream for both bot and user sessions. Bearer auth required. No replay buffer; `Last-Event-ID` is logged but ignored. `retry:` hint sent at stream start.
- **Inbound delivery is SSE-only**: `GET /events/telegram` is the only supported path for inbound Telegram events in HTTP multi-user mode. Callback-style delivery is not supported.
- **Duplicate active bot tokens rejected**: multi-user auth forbids the same live bot token under different bearers.

## Project-Specific Constraints

- SSE is bearer-only on both `/mcp` and `GET /events/telegram`.
- Native browser `EventSource` is not supported in v1 because it cannot attach the required `Authorization` header.
- `GET /events/telegram` is live-only in v1. No replay buffer, no resume support. `Last-Event-ID` is logged but ignored. `retry:` hint sent at stream start.
- No WebSocket transport for Telegram events.
- `callback_url` is not supported for inbound event delivery. Relay flows are for setup and auth only.
- Do not confuse `transports/credential_store.py` with multi-user bearer/session persistence.

## Documentation

- Module docstrings are expected
- Google-style docstrings are common
- Section separators use `# ---------------------------------------------------------------------------`

## Commits

Conventional Commits: `type(scope): message`. Semantic release is configured.

## Pre-commit Hooks

1. gitleaks
2. Ruff lint + format
3. ty type check
4. pytest (`--timeout=30 --tb=short -q`)

## TODO / Backlog

- [ ] **Glama display name**: Cannot set programmatically. Update manually via Glama admin page.
