# AGENTS.md - backends/

**OVERVIEW:** Dual-mode backend abstraction (Bot API via httpx, MTProto via Telethon) with security hardening.

## WHERE TO LOOK

**base.py** (155 lines)
- `TelegramBackend` ABC: 15 abstract methods (connect, auth, messages, chats, media, contacts)
- `ModeError`: Raised when action requires different mode (bot vs user)
- `ensure_mode(required)`: Guard method, throws if mode mismatch

**bot_backend.py** (299 lines)
- `BotBackend`: httpx client, stateless Bot API wrapper
- `_call(method, **params)`: JSON POST to `api.telegram.org/bot{token}/{method}`
- `_call_form(method, files, **params)`: Multipart form for file uploads
- Bot limitations: No `search_messages`, `list_chats`, `get_history` (returns empty/raises `ModeError`)
- Contact methods: All raise `ModeError` (user-only)
- `asyncio.to_thread(path.read_bytes)`: Async file reads to prevent blocking

**user_backend.py** (520 lines, largest file)
- `UserBackend`: Telethon MTProto client, full user account access
- Session file: `~/.better-telegram-mcp/{session_name}.session`, created with 0o600 permissions
- `_serialize_message/dialog/user`: Convert Telethon objects to dicts
- `iter_messages/iter_dialogs/iter_participants`: Async comprehensions (faster, less memory than `get_*` methods)
- Auth flow: `send_code()` -> `sign_in(phone, code, password=None)`
- `_ensure_client()`: Runtime check that `connect()` was called

**bot_update_producer.py**
- `BotPollingBackend`: Protocol type for `_call`, `get_updates`, `_bot_info`; auth provider resolves via `isinstance(backend, BotBackend)` not duck-typing
- `BotUpdateProducer`: Long-polls Bot API `getUpdates`, publishes normalized event envelopes
- Offset persistence: debounced via `_persist_offset()` (default 5s interval), final flush on `stop()`
- `_drain_backlog_to_live_boundary()`: Skips existing updates on first start (no replay)
- Exponential backoff on transient errors, immediate stop on auth errors (401/403)
- `offset_persist_interval_seconds` constructor param controls I/O frequency

**security.py** (140 lines)
- `validate_url(url)`: SSRF protection (blocks private IPs, metadata endpoints, DNS rebinding)
- `validate_file_path(file_path)`: Path traversal prevention (blocks `/etc`, `/proc`, dotfiles, sensitive dirs)
- `validate_output_dir(output_dir)`: Write protection (blocks system dirs, hidden dirs)
- `_BLOCKED_NETWORKS`: 11 private/internal IP ranges (127.0.0.0/8, 10.0.0.0/8, etc.)
- `socket.getaddrinfo()`: Resolve hostnames to IPs before allowing access (prevents DNS rebinding)

## CONVENTIONS

**Mode detection:**
- Bot mode: `TELEGRAM_BOT_TOKEN` set
- User mode: `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` + `TELEGRAM_PHONE` set
- Tools call `ensure_mode("user")` to guard user-only actions

**Error handling:**
- `ModeError`: Wrong mode for action (bot trying user-only feature)
- `SecurityError`: SSRF/path traversal attempt blocked
- `TelegramAPIError`: Bot API error response (has `error_code` attribute)
- Return empty lists/dicts for unsupported operations instead of raising (bot history, search)

**Async patterns:**
- `async for` comprehensions over `iter_*` methods (Telethon) instead of `get_*` (avoids intermediate TotalList allocation)
- `asyncio.to_thread()` for sync I/O (file reads) to prevent blocking event loop
- `asyncio.iscoroutine()` check for Telethon's `is_connected()` (sync method that may return coroutine)

**Session security:**
- Pre-create session file with `os.open(..., 0o600)` before Telethon writes to it (prevents TOCTOU)
- `os.chmod(session_file, 0o600)` after sign-in to secure existing sessions from older versions
- Data dir: `~/.better-telegram-mcp/`, created with 0o700 permissions

## ANTI-PATTERNS

- **DON'T** use `get_messages()`, `get_dialogs()`, `get_participants()` (Telethon). Use `iter_*` variants in async comprehensions.
- **DON'T** skip security validation. Always call `validate_url()`, `validate_file_path()`, `validate_output_dir()` before external access.
- **DON'T** assume `is_connected()` is sync. Check `asyncio.iscoroutine()` for Telethon compatibility.
- **DON'T** create session files without secure permissions. Use `os.open()` with 0o600 before Telethon writes.
- **DON'T** raise exceptions for mode mismatches in backend methods. Use `ensure_mode()` or return empty results.
- **DON'T** use `path.read_bytes()` directly. Wrap in `asyncio.to_thread()` to prevent blocking.
- **DON'T** persist bot polling offset on every poll batch — use debounced `_persist_offset()` and rely on `stop()` for final flush.
