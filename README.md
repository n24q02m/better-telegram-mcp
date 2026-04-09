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

## Shared HTTP Event Relay

The server can optionally forward **all inbound raw Telegram updates from all authenticated user sessions** to **one shared external HTTP endpoint**.

This relay is:
- **optional** -- existing MCP behavior stays unchanged when it is not configured
- **env-only in v1** -- there is no runtime API for changing relay settings
- **multi-user aware** -- every payload includes the account that received the event
- **user-mode only** -- bot-mode inbound event capture is not part of this feature

### When it works

The shared relay is used in **HTTP multi-user mode**.

Multi-user HTTP mode requires:
- `TRANSPORT_MODE=http`
- `PUBLIC_URL`
- `DCR_SERVER_SECRET`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

Relay delivery is enabled only when `TELEGRAM_RELAY_ENDPOINT_URL` is also set.

### Quick setup

To enable delivery, set **all** of the following env vars and start the server in HTTP multi-user mode:

```bash
export TRANSPORT_MODE=http
export PUBLIC_URL="https://your-public-host.example.com"
export DCR_SERVER_SECRET="replace-with-a-random-secret"
export TELEGRAM_API_ID="123456"
export TELEGRAM_API_HASH="your_api_hash"
export TELEGRAM_RELAY_ENDPOINT_URL="https://your-endpoint.example.com/telegram-events"

uv run better-telegram-mcp
```

Setting these env vars enables the relay, but events are sent only for **user accounts that have actually been authenticated and connected** through the HTTP multi-user flow.

Once a user account is authenticated and connected, the server starts POSTing JSON events for that account to `TELEGRAM_RELAY_ENDPOINT_URL`.

### Relay Environment Variables

| Variable | Default | Description |
|:--|:--|:--|
| `TELEGRAM_RELAY_ENDPOINT_URL` | unset | Shared external HTTP endpoint that receives JSON event payloads |
| `TELEGRAM_RELAY_QUEUE_SIZE` | `10000` | Max in-memory queued events before new events are dropped |
| `TELEGRAM_RELAY_TIMEOUT_SECONDS` | `10` | HTTP request timeout per delivery attempt |
| `TELEGRAM_RELAY_MAX_RETRIES` | `5` | Max retry attempts for transient failures |
| `TELEGRAM_RELAY_BACKOFF_INITIAL_MS` | `500` | Initial retry backoff in milliseconds |
| `TELEGRAM_RELAY_BACKOFF_MAX_MS` | `30000` | Max retry backoff in milliseconds |

`TELEGRAM_RELAY_ENDPOINT_URL` is validated with the same SSRF protections used elsewhere in the project. Internal/private/localhost targets are rejected.

### Delivery Behavior

- **Payload format:** JSON
- **Scope:** all raw Telethon updates from authorized user sessions
- **Destination:** one shared process-wide endpoint
- **Guarantee:** **at-least-once**
- **Duplicates:** possible during retries or reconnect catch-up; dedupe downstream by `event_id`
- **Retry policy:** retries only on timeout/network failures, HTTP `429`, and `5xx`
- **No retry:** other `4xx` responses are treated as terminal failures
- **Backpressure:** queue overflow drops new events instead of blocking Telegram update processing
- **Durability:** **in-memory only in v1**; queued events can be lost on process crash or prolonged outage
- **Outbound auth:** none in v1

### Payload Shape

Each event contains:
- `event_id` -- deterministic SHA-256 hash derived from `account.telegram_user_id` and the canonical raw update JSON
- `event_type` -- raw Telegram update type from the update `_` field, e.g. `UpdateNewMessage`
- `occurred_at` -- server-side ISO 8601 timestamp when the envelope was created
- `account.telegram_user_id` -- stable Telegram account ID
- `account.session_name` -- local session name used by this server
- `account.username` -- included when Telegram provides it
- `update` -- raw `update.to_dict()` payload

The payload intentionally does **not** include bearer tokens or phone numbers.

Your endpoint should expect a JSON envelope with account metadata plus raw Telegram update data. The `update` field can contain different Telegram update types, not only `UpdateNewMessage`.

### Example Payload

The JSON below is **one `UpdateNewMessage` example**. The nested shape inside `update` varies by Telegram update type.

```json
{
  "event_id": "8c85b6dcf7b6ef2d7d4f0d5536f8b2aa8520bc0bcf5d3eaa541d5f5bc9d5db8a",
  "event_type": "UpdateNewMessage",
  "occurred_at": "2026-04-09T09:15:30.123456+00:00",
  "account": {
    "telegram_user_id": 123456789,
    "session_name": "default",
    "username": "example_user"
  },
  "update": {
    "_": "UpdateNewMessage",
    "message": {
      "_": "Message",
      "id": 42,
      "message": "hello"
    }
  }
}
```

### Operator Notes

- Pending OTP sessions do **not** emit relay events until authentication is completed.
- Relay delivery is intentionally isolated from MCP tools/resources; events are pushed externally, not exposed as MCP subscriptions.
- `/health` in multi-user HTTP mode exposes only `relay_enabled: true|false` and does not leak the relay URL.

## Build from Source

```bash
git clone https://github.com/n24q02m/better-telegram-mcp.git
cd better-telegram-mcp
uv sync
uv run better-telegram-mcp
```

## License

MIT -- See [LICENSE](LICENSE).
