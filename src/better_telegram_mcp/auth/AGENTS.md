# AGENTS.md - auth/

**Authentication and session management for multi-user Telegram MCP server.**

## OVERVIEW

Per-user session storage, OTP flow, bearer token lifecycle. Bot mode (instant) + user mode (Telethon OTP). Encrypted session persistence with AES-256-GCM.

## WHERE TO LOOK

```
telegram_auth_provider.py    # Main auth orchestrator, bearer -> backend mapping
per_user_session_store.py     # Encrypted session persistence (AES-256-GCM)
stateless_client_store.py     # HMAC-based OAuth client registration (DCR)
```

### telegram_auth_provider.py

- `TelegramAuthProvider`: Manages bearer -> `TelegramBackend` lifecycle
- `TelegramBearerRuntime`: Per-bearer state (backend, `SSESubscriberHub`, bot_producer typed `BotUpdateProducer | None`)
- `register_bot()`: Instant bot registration (validates token via getMe), starts polling producer
- `start_user_auth()`: Sends OTP code, stores pending state
- `complete_user_auth()`: Atomic pop from pending, verifies OTP, persists session, installs event sink; restores pending on sign-in failure
- `restore_sessions()`: Parallel session restoration on startup (asyncio.gather)
- `revoke_session()`: Stop producer, close hub, disconnect backend, delete session
- `cleanup_expired()`: Remove sessions older than 30 days + stale pending OTPs (>5 min); called periodically by lifespan task
- `_start_bot_producer()`: Verifies backend is `BotBackend` via `isinstance` (local import) before creating producer; logs warning if check fails
- `_stop_bot_producer()`: Direct `await producer.stop()` (typed field, no getattr)

### per_user_session_store.py

- `PerUserSessionStore`: Single encrypted file (`sessions.enc`) for all users
- `SessionInfo`: Dataclass with mode, credentials, created_at
- Key derivation: PBKDF2-HMAC-SHA256, 600k iterations
- Salt migration: Legacy hardcoded -> random 16-byte (on first write)
- File permissions: 600 (owner read/write only)

### stateless_client_store.py

- `StatelessClientStore`: HMAC-based OAuth client registration
- Derives deterministic `client_id` and `client_secret` from redirect_uris + client_name
- Warm cache for full metadata, fallback to derived secret on cold start
- Idempotent: same input always produces same credentials

## CONVENTIONS

### Session Files

- Location: `~/.better-telegram-mcp/sessions.enc` (encrypted), `~/.better-telegram-mcp/user_sessions/*.session` (Telethon)
- Permissions: 600 (enforced via `stat.S_IRUSR | stat.S_IWUSR`)
- Naming: SHA256(bearer)[:16] for session file names
- TTL: 30 days (`_SESSION_TTL = 30 * 24 * 60 * 60`)

### Encryption

- Algorithm: AES-256-GCM
- Key derivation: PBKDF2-HMAC-SHA256, 600k iterations
- Nonce: 12 bytes random (prepended to ciphertext)
- Secret source: `CREDENTIAL_SECRET` env var or auto-generated `.secret` file

### OTP Flow

1. `start_user_auth(bearer, phone)` -> sends code, returns `phone_code_hash`
2. Store pending state: `_pending_otps[bearer] = _PendingOTP(bearer, backend, phone, ...)`
3. `complete_user_auth(bearer, code, password?)` -> sign in, persist session
4. Pending OTP TTL: 5 minutes (cleaned up in `cleanup_expired()`)

### Parallel Restoration

- `restore_sessions()` uses `asyncio.gather()` to connect all backends concurrently
- Drastically reduces startup time for multi-user deployments
- Failed restorations are logged and removed from store

## ANTI-PATTERNS

- **Don't** store 2FA passwords in env vars or session files (OTP only, entered via web UI)
- **Don't** reuse bearer tokens across MCP sessions (each session gets unique bearer)
- **Don't** skip permission checks on session files (600 required for security)
- **Don't** use sequential restoration (kills startup time with many users)
- **Don't** persist OAuth client metadata in database (use HMAC derivation for stateless DCR)
- **Don't** hardcode salt (migrated to random 16-byte on first write for forward security)
- **Don't** use `getattr`/duck-typing for `bot_producer` — field is typed `BotUpdateProducer | None`, call `.stop()` directly
- **Don't** use duck-typing/inspect for bot polling backend check — use `isinstance(backend, BotBackend)` via local import to avoid test patch interference
- **Don't** silently skip producer startup on backend mismatch — always log a warning so missing SSE events are diagnosable
