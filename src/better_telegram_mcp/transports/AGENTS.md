# AGENTS.md - transports

## Overview

HTTP transport bootstrap and request-layer behavior live here: single-user HTTP fallback, multi-user bearer-authenticated HTTP mode, `/mcp`, `GET /events/telegram`, and encrypted single-user credential storage.

## Structure

```
transports/
  http.py               # Mode split, startup wiring, ContextVar bridge
  http_multi_user.py    # Starlette app, auth routes, /mcp, /events/telegram
  credential_store.py   # Encrypted single-user HTTP credential persistence
```

## Where To Look

| Task | File | Notes |
|---|---|---|
| Decide single-user vs multi-user HTTP mode | `http.py` | `_is_multi_user_mode()` gates the split |
| Start HTTP server and wire app | `http.py` | `start_http()` is the transport entry |
| Per-request backend injection | `http.py` | `_current_backend` is the ContextVar bridge |
| Auth endpoints and bearer extraction | `http_multi_user.py` | `/auth/*` plus `_extract_bearer()` |
| `/mcp` request auth wrapper | `http_multi_user.py` | `BearerAuthMCPApp` injects backend before delegating |
| SSE framing and stream lifecycle | `http_multi_user.py` | `telegram_events()` + `_format_sse_event()` |
| Encrypted credential persistence | `credential_store.py` | Single-user fallback only |

## Conventions

- `http.py` owns transport startup and mode selection, not the detailed route behavior.
- `http_multi_user.py` owns Starlette routes, auth JSON responses, rate limiting (with bounded eviction at 10K keys), health checks, and SSE stream behavior.
- `_current_backend` is the only supported bridge for per-request backend injection into MCP handlers.
- `credential_store.py` persists single-user HTTP credentials under `data_dir`; it is not the multi-user auth/session store.
- Multi-user runtime ownership lives in `auth/telegram_auth_provider.py`; transport consumes that provider instead of duplicating session rules here.

## SSE-Specific Rules

- SSE endpoint is `GET /events/telegram`.
- Authentication is bearer-only via `Authorization: Bearer ...`.
- Stream is live-only in v1: no replay buffer, no resume semantics. `Last-Event-ID` is logged at debug level but ignored. `retry:` hint sent at stream start.
- Heartbeats are explicit SSE events, not comment frames.
- Per-bearer isolation is required; a bearer must only receive its own Telegram events.
- Current v1 behavior allows one active SSE connection per bearer; replacement closes the older stream with an error event.
- Native browser `EventSource` is not a supported client in v1 because it cannot send the required bearer header.

## Anti-Patterns

- Do not implement callback-style delivery for inbound Telegram events; SSE is the only supported delivery path.
- Do not document or implement `callback_url` semantics for inbound event delivery.
- Do not bypass bearer extraction or `_current_backend` injection for `/mcp`.
- Do not treat `credential_store.py` as the multi-user bearer/session database.
- Do not document `events/` as an independent user-facing subsystem yet; transport owns the operational contract.
- Do not add WebSocket assumptions to Telegram event delivery docs or code.

## Verification Notes

- Transport changes usually need targeted checks in `tests/test_http_multi_user.py` and, when SSE behavior changes, the SSE-focused tests (`tests/test_sse_integration.py`, `tests/test_sse_fanout_hub.py`, `tests/test_bot_update_producer.py`).
- When changing auth/runtime wiring, also inspect provider tests such as `tests/test_telegram_auth_provider.py` because the transport layer depends on provider-owned runtimes.
