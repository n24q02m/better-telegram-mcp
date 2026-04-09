# Better Telegram MCP

mcp-name: io.github.n24q02m/better-telegram-mcp

**MCP server for Telegram with dual-mode support: Bot API (httpx) for quick bot integrations and MTProto (Telethon) for full user-account access.**

<!-- Badge Row 1: Status -->
[![CI](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/n24q02m/better-telegram-mcp/graph/badge.svg?token=d0fef60a-542e-4be2-9528-6e3a12931067)](https://codecov.io/gh/n24q02m/better-telegram-mcp)
[![PyPI](https://img.shields.io/pypi/v/better-telegram-mcp?logo=pypi&logoColor=white)](https://pypi.org/project/better-telegram-mcp/)
[![Docker](https://img.shields.io/docker/v/n24q02m/better-telegram-mcp?label=docker&logo=docker&logoColor=white&sort=semver)](https://hub.docker.com/r/n24q02m/better-telegram-mcp)
[![License: MIT](https://img.shields.io/github/license/n24q02m/better-telegram-mcp)](https://opensource.org/licenses/MIT)

<!-- Badge Row 2: Tech -->
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](#)
[![Telegram](https://img.shields.io/badge/Telegram-Bot_API_+_MTProto-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org)
[![MCP](https://img.shields.io/badge/MCP-000000?logo=anthropic&logoColor=white)](#)
[![semantic-release](https://img.shields.io/badge/semantic--release-e10079?logo=semantic-release&logoColor=white)](https://github.com/python-semantic-release/python-semantic-release)
[![Renovate](https://img.shields.io/badge/renovate-enabled-1A1F6C?logo=renovatebot&logoColor=white)](https://github.com/renovatebot/renovate)

<a href="https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp/badge" alt="better-telegram-mcp MCP server" />
</a>

## Features

- **Dual mode** -- Bot API (httpx) for bots, MTProto (Telethon) for user accounts
- **6 tools** with action dispatch: `message`, `chat`, `media`, `contact`, `config`, `help`
- **Auto-detect mode** -- Set bot token for bot mode, or API credentials for user mode
- **Web-based OTP auth** -- Browser-based authentication with remote relay support for headless environments
- **Tool annotations** -- Each tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **MCP Resources** -- Documentation available as `telegram://docs/*` resources
- **Security hardened** -- SSRF protection, path traversal prevention, error sanitization

## Setup

**With AI Agent** -- copy and send this to your AI agent:

> Please set up better-telegram-mcp for me. Follow this guide:
> https://raw.githubusercontent.com/n24q02m/better-telegram-mcp/main/docs/setup-with-agent.md

**Manual Setup** -- follow [docs/setup-manual.md](docs/setup-manual.md)

## Tools

| Tool | Actions | Description |
|:-----|:--------|:------------|
| `message` | `send`, `edit`, `delete`, `forward`, `pin`, `react`, `search`, `history` | Send, edit, delete, forward messages. Pin, react, search, browse history |
| `chat` | `list`, `info`, `create`, `join`, `leave`, `members`, `admin`, `settings`, `topics` | List and manage chats, groups, channels. Members, admin, forum topics |
| `media` | `send_photo`, `send_file`, `send_voice`, `send_video`, `download` | Send photos, files, voice notes, videos. Download media from messages |
| `contact` | `list`, `search`, `add`, `block` | List, search, add contacts. Block/unblock users (user mode only) |
| `config` | `status`, `set`, `cache_clear`, `setup_status`, `setup_start`, `setup_reset`, `setup_complete` | Server status, runtime settings, cache, credential setup (relay, status, reset, complete) |
| `help` | -- | Full documentation for any topic |

### MCP Resources

| URI | Content |
|:----|:--------|
| `telegram://docs/messages` | Message operations reference |
| `telegram://docs/chats` | Chat management reference |
| `telegram://docs/media` | Media send/download reference |
| `telegram://docs/contacts` | Contact management reference |
| `telegram://stats` | All documentation combined |

## Security

- **SSRF Protection** -- All URLs validated against internal/private IP ranges, DNS rebinding blocked
- **Path Traversal Prevention** -- File paths validated, sensitive directories blocked
- **Session File Security** -- 600 permissions, 2FA via web UI only (never stored in env vars)
- **Error Sanitization** -- Credentials never leaked in error messages

## SSE vs Relay Dispatcher

This project exposes two separate features that should not be conflated:

- **Relay dispatcher** -- callback-style delivery used for relay setup and external integration flows.
- **HTTP SSE stream** -- the live event stream at `GET /events/telegram`.

Key rules:

- **SSE is bearer-only.** Clients must send `Authorization: Bearer ...` on both `/mcp` and `GET /events/telegram`.
- **SSE does not accept `callback_url`.** It is not a callback subscription API.
- **Relay web UI auth is for relay setup**, not for authenticating SSE clients.

## Unified HTTP SSE Stream

In HTTP multi-user mode, the server exposes one shared live event stream at `GET /events/telegram`.

This flow is:
- **bearer-authenticated only** -- the same bearer used for `/mcp` must be sent in the `Authorization: Bearer ...` header
- **shared across user and bot sessions** -- user mode publishes raw Telethon updates, bot mode publishes Bot API long-poll updates
- **live-only in v1** -- no replay buffer, no resume support, and `Last-Event-ID` is ignored
- **honest about delivery** -- if no SSE client is connected, events are not buffered for later subscribers

### When it works

The unified SSE endpoint is available in **HTTP multi-user mode**.

Multi-user HTTP mode requires:
- `TRANSPORT_MODE=http`
- `PUBLIC_URL`
- `DCR_SERVER_SECRET`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

Then authenticate a bot or user session through the HTTP auth flow and open `GET /events/telegram` with that bearer token.

This HTTP auth flow is the bearer issuance flow for SSE access. It is separate from relay setup.

### Request model

- **Write path:** `POST /mcp`
- **Read path:** `GET /events/telegram`
- **Auth:** `Authorization: Bearer <token>` header only

Native browser EventSource is **not supported** in v1 because it cannot send the required `Authorization` header. Use `curl`, `httpx`, or a custom `fetch()`/stream reader instead.

### Quick setup

Start the server in HTTP multi-user mode:

```bash
export TRANSPORT_MODE=http
export PUBLIC_URL="https://your-public-host.example.com"
export DCR_SERVER_SECRET="replace-with-a-random-secret"
export TELEGRAM_API_ID="123456"
export TELEGRAM_API_HASH="your_api_hash"

uv run better-telegram-mcp
```

Authenticate a Telegram session through the HTTP auth endpoints, then connect to the SSE stream with the returned bearer:

```bash
curl -N \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: text/event-stream" \
  "https://your-public-host.example.com/events/telegram"
```

Equivalent clients can be built with `httpx` or a custom `fetch()` stream reader.

### Delivery behavior

- **One shared SSE endpoint:** `GET /events/telegram`
- **Per-bearer isolation:** a bearer only receives its own Telegram events
- **User support:** raw Telethon updates after successful user auth
- **Bot support:** Bot API long polling with durable offset persistence
- **Live-only:** missed events are not replayed to later subscribers
- **No replay semantics:** `Last-Event-ID` is ignored and there is no server-side event history
- **Single active connection in v1:** a second connection for the same bearer closes the first with `event: error` and `{"reason":"connection_replaced"}`
- **Overflow behavior:** if the per-subscriber queue fills, the stream closes with `event: error` and `{"reason":"overflow"}`
- **Runtime stop behavior:** revoke or shutdown closes the stream with `event: error` and `{"reason":"runtime_stopped"}`
- **No subscriber attached:** events are dropped instead of being buffered for replay
- **Duplicate bot tokens:** the same active bot token cannot be registered under multiple bearers in v1

### Event payload

Each SSE message carries the full unified JSON envelope in the `data:` field:

- `event_id` -- deterministic SHA-256 hash derived from normalized account identity and the canonical raw update JSON
- `event_type` -- raw Telegram update type such as `UpdateNewMessage`
- `occurred_at` -- server-side ISO 8601 timestamp when the envelope was created
- `mode` -- `"user"` or `"bot"`
- `account.telegram_id` -- stable Telegram account or bot ID
- `account.session_name` -- local session name used by this server
- `account.username` -- included when Telegram provides it
- `account.mode` -- `"user"` or `"bot"`
- `update` -- raw update payload

The payload intentionally does **not** include bearer tokens or phone numbers.

### Example SSE frame

```text
id: 8c85b6dcf7b6ef2d7d4f0d5536f8b2aa8520bc0bcf5d3eaa541d5f5bc9d5db8a
event: UpdateNewMessage
data: {"event_id":"8c85b6dcf7b6ef2d7d4f0d5536f8b2aa8520bc0bcf5d3eaa541d5f5bc9d5db8a","event_type":"UpdateNewMessage","occurred_at":"2026-04-09T09:15:30.123456+00:00","mode":"user","account":{"telegram_id":123456789,"session_name":"default","username":"example_user","mode":"user"},"update":{"_":"UpdateNewMessage","message":{"_":"Message","id":42,"message":"hello"}}}
```

### v1 restrictions

- No callback URL subscription API for the SSE stream
- No webhook subscription API for clients
- No WebSocket transport for Telegram events
- No replay buffer or resume support
- No browser-auth workaround for native browser EventSource

The relay dispatcher remains available as a separate feature and is not part of these SSE restrictions.

## Build from Source

```bash
git clone https://github.com/n24q02m/better-telegram-mcp.git
cd better-telegram-mcp
uv sync
uv run better-telegram-mcp
```

## License

MIT -- See [LICENSE](LICENSE).
