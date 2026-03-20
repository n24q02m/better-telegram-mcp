# Better Telegram MCP

mcp-name: io.github.n24q02m/better-telegram-mcp

**MCP server for Telegram with dual-mode support: Bot API (httpx) for quick bot integrations and MTProto (Telethon) for full user-account access.**

[![CI](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/n24q02m/better-telegram-mcp/graph/badge.svg?token=d0fef60a-542e-4be2-9528-6e3a12931067)](https://codecov.io/gh/n24q02m/better-telegram-mcp)
[![PyPI](https://img.shields.io/pypi/v/better-telegram-mcp?logo=pypi&logoColor=white)](https://pypi.org/project/better-telegram-mcp/)
[![Docker](https://img.shields.io/docker/v/n24q02m/better-telegram-mcp?label=docker&logo=docker&logoColor=white&sort=semver)](https://hub.docker.com/r/n24q02m/better-telegram-mcp)
[![License: MIT](https://img.shields.io/github/license/n24q02m/better-telegram-mcp)](https://opensource.org/licenses/MIT)

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
- **6 mega-tools** with action dispatch: `messages`, `chats`, `media`, `contacts`, `config`, `help`
- **Token optimization** -- 6 tools instead of 30+ individual endpoints (~80% token reduction)
- **Tool annotations** -- Each tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **MCP Resources** -- Documentation available as `telegram://docs/*` resources
- **Auto-detect mode** -- Set bot token for bot mode, or API credentials for user mode
- **Web-based OTP auth** -- Browser-based authentication with remote relay support for headless environments
- **Security hardened** -- SSRF protection, path traversal prevention, error sanitization

---

## Quick Start

### Prerequisites

- **Python 3.13** (required -- Python 3.14+ is **not** supported)

### Bot Mode

1. Open Telegram, search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, follow prompts to name your bot
3. Copy the token (format: `123456789:ABCdefGHI-JKLmnoPQRstUVwxyz`)
4. Run:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF uvx --python 3.13 better-telegram-mcp
```

### User Mode

1. Go to [https://my.telegram.org](https://my.telegram.org), login with your phone number
2. Click "API development tools", create an app
3. Note your `api_id` (integer) and `api_hash` (32-char hex string)
4. Add to your MCP config with all required env vars (see [MCP Config Examples](#mcp-config-examples) below)
5. Start using -- on first run, a **local web page** opens in your browser for OTP authentication:
   - Click "Send OTP Code" to receive a code in your **Telegram app** (not SMS)
   - Enter the OTP code on the web page
   - If 2FA is enabled, enter your password on the same page
   - Headless (Docker/SSH): use `curl` to hit the same endpoints (URL shown in logs/error messages)
6. Done -- session file persists at `~/.better-telegram-mcp/<name>.session`, no more auth needed on subsequent runs

> **Security**: The session file has `600` permissions (owner-only). Treat it like a password -- anyone with this file can access your Telegram account.

---

## MCP Config Examples

### Claude Code

```bash
# Bot mode
claude mcp add telegram -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF -- uvx --python 3.13 better-telegram-mcp

# User mode (auto-auth on first run)
claude mcp add telegram \
  -e TELEGRAM_API_ID=12345 \
  -e TELEGRAM_API_HASH=abc123 \
  -e TELEGRAM_PHONE=+1234567890 \
  -- uvx --python 3.13 better-telegram-mcp
```

### Claude Desktop / Cursor

Bot mode:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uvx",
      "args": ["--python", "3.13", "better-telegram-mcp"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"
      }
    }
  }
}
```

User mode:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uvx",
      "args": ["--python", "3.13", "better-telegram-mcp"],
      "env": {
        "TELEGRAM_API_ID": "12345678",
        "TELEGRAM_API_HASH": "your-api-hash-from-my-telegram-org",
        "TELEGRAM_PHONE": "+1234567890"
      }
    }
  }
}
```

### VS Code Copilot

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "telegram": {
      "command": "uvx",
      "args": ["--python", "3.13", "better-telegram-mcp"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"
      }
    }
  }
}
```

### Docker

```bash
# Bot mode
docker run -i --rm -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF n24q02m/better-telegram-mcp

# User mode (mount session dir for persistence)
docker run -i --rm \
  -e TELEGRAM_API_ID=12345 \
  -e TELEGRAM_API_HASH=abcdef123456 \
  -e TELEGRAM_PHONE=+84912345678 \
  -v ~/.better-telegram-mcp:/data \
  n24q02m/better-telegram-mcp
```

Docker config for MCP clients:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TELEGRAM_BOT_TOKEN",
        "-v", "telegram-data:/data",
        "n24q02m/better-telegram-mcp"
      ],
      "env": {
        "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"
      }
    }
  }
}
```

> **Note**: For user mode in Docker, mount the session directory with `-v ~/.better-telegram-mcp:/data` so the session persists across container restarts. On first run, the auth web server starts -- use port mapping or `curl` to complete auth.

---

## Configuration

All configuration is via environment variables with `TELEGRAM_` prefix:

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Bot mode | -- | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_ID` | User mode | -- | API ID from [my.telegram.org](https://my.telegram.org) (integer) |
| `TELEGRAM_API_HASH` | User mode | -- | API hash from [my.telegram.org](https://my.telegram.org) (32-char hex) |
| `TELEGRAM_PHONE` | User mode | -- | Phone number with country code (e.g., `+84912345678`). Required for web auth UI. |
| `TELEGRAM_AUTH_URL` | No | `https://better-telegram-mcp.n24q02m.com` | Auth relay URL. Set `local` for localhost-only mode, or a custom URL for self-hosted relay. |
| `TELEGRAM_SESSION_NAME` | No | `default` | Session file name (useful for multiple accounts) |
| `TELEGRAM_DATA_DIR` | No | `~/.better-telegram-mcp` | Data directory for session files |

**Mode detection**: If `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` are set, user mode is used (priority). Otherwise, `TELEGRAM_BOT_TOKEN` is used for bot mode. No silent fallback between modes -- if neither is set, the server exits with an error.

---

## Tools

### `messages` -- send|edit|delete|forward|pin|react|search|history

Send, edit, delete, forward messages. Pin messages, add reactions. Search messages and browse history (user mode only).

| Action | Required params | Optional params | Mode |
|:-------|:----------------|:----------------|:-----|
| `send` | `chat_id`, `text` | `reply_to`, `parse_mode` | Bot + User |
| `edit` | `chat_id`, `message_id`, `text` | `parse_mode` | Bot + User |
| `delete` | `chat_id`, `message_id` | | Bot + User |
| `forward` | `from_chat`, `to_chat`, `message_id` | | Bot + User |
| `pin` | `chat_id`, `message_id` | | Bot + User |
| `react` | `chat_id`, `message_id`, `emoji` | | Bot + User |
| `search` | `query` | `chat_id`, `limit` | User only |
| `history` | `chat_id` | `limit`, `offset_id` | User only |

### `chats` -- list|info|create|join|leave|members|admin|settings|topics

List and manage chats, groups, channels. Create groups/channels, join/leave, manage members and admins, update settings, manage forum topics.

| Action | Required params | Optional params | Mode |
|:-------|:----------------|:----------------|:-----|
| `list` | | `limit` | User only |
| `info` | `chat_id` | | Bot + User |
| `create` | `title` | `is_channel` | User only |
| `join` | `link_or_hash` | | Partial + User |
| `leave` | `chat_id` | | Partial + User |
| `members` | `chat_id` | `limit` | Bot + User |
| `admin` | `chat_id`, `user_id` | `demote` | Bot + User |
| `settings` | `chat_id` + at least one of `title`/`description` | | Bot + User |
| `topics` | `chat_id`, `topic_action` | `topic_id`, `topic_name` | Partial + User |

### `media` -- send_photo|send_file|send_voice|send_video|download

Send photos, files, voice notes, and videos. Download media from messages (user mode only).

| Action | Required params | Optional params | Mode |
|:-------|:----------------|:----------------|:-----|
| `send_photo` | `chat_id`, `file_path_or_url` | `caption` | Bot + User |
| `send_file` | `chat_id`, `file_path_or_url` | `caption` | Bot + User |
| `send_voice` | `chat_id`, `file_path_or_url` | `caption` | Bot + User |
| `send_video` | `chat_id`, `file_path_or_url` | `caption` | Bot + User |
| `download` | `chat_id`, `message_id` | `output_dir` | User only |

### `contacts` -- list|search|add|block (user mode only)

List, search, add contacts. Block and unblock users.

| Action | Required params | Optional params |
|:-------|:----------------|:----------------|
| `list` | | |
| `search` | `query` | |
| `add` | `phone`, `first_name` | `last_name` |
| `block` | `user_id` | `unblock` |

### `config` -- status|set|cache_clear

Check server status, update runtime settings, clear cache. Works in both modes. Does not require authentication.

| Action | Required params | Optional params |
|:-------|:----------------|:----------------|
| `status` | | |
| `set` | at least one of `message_limit`/`timeout` | |
| `cache_clear` | | |

### `help` -- Documentation lookup

Returns full documentation for any tool.

| Param | Values |
|:------|:-------|
| `topic` | `messages`, `chats`, `media`, `contacts`, `all` |

---

## Mode Capabilities

| Feature | Bot Mode | User Mode |
|:--------|:--------:|:---------:|
| Send messages | Y | Y |
| Edit messages | Y | Y |
| Delete messages | Y | Y |
| Forward messages | Y | Y |
| Pin messages | Y | Y |
| React to messages | Y | Y |
| Search messages | -- | Y |
| Browse history | -- | Y |
| List chats | -- | Y |
| Get chat info | Y | Y |
| Create groups/channels | -- | Y |
| Join/Leave chats | Partial | Y |
| Manage members | Y | Y |
| Admin promotion | Y | Y |
| Chat settings | Y | Y |
| Forum topics | Partial | Y |
| Send media (photo/file/voice/video) | Y | Y |
| Download media | -- | Y |
| List contacts | -- | Y |
| Search contacts | -- | Y |
| Add contacts | -- | Y |
| Block/Unblock users | -- | Y |
| Config (status/set/cache) | Y | Y |

---

## MCP Resources

Documentation is also available as MCP resources that AI agents can read directly:

| URI | Content |
|:----|:--------|
| `telegram://docs/messages` | Message operations reference |
| `telegram://docs/chats` | Chat management reference |
| `telegram://docs/media` | Media send/download reference |
| `telegram://docs/contacts` | Contact management reference |
| `telegram://stats` | All documentation combined |

---

## Auth Flow

Authentication is only needed for **user mode** (MTProto). Bot mode uses a static token and requires no auth flow.

### How it works

1. On first run, if the session is not authenticated, the server starts a **web-based auth UI**
2. A browser opens automatically (or the URL is logged for headless environments)
3. User clicks "Send OTP Code" -- an OTP is sent to the **Telegram app** (not SMS)
4. User enters the OTP code on the web page
5. If 2FA is enabled, user enters the 2FA password on the same page
6. Session file is saved at `~/.better-telegram-mcp/<name>.session` with `600` permissions
7. `_pending_auth` flag clears immediately -- tools become active without restart

### Auth modes (TELEGRAM_AUTH_URL)

| Mode | `TELEGRAM_AUTH_URL` value | Use case |
|:-----|:--------------------------|:---------|
| **Remote** (default) | `https://better-telegram-mcp.n24q02m.com` | Headless, SSH, Docker -- any browser anywhere |
| **Self-hosted** | `https://your-domain.com` | Custom relay deployment |
| **Local** | `local` | Desktop, offline, no external server |

**Remote mode**: The MCP server creates a session on the relay server, then polls for commands (send_code, verify). The relay server only relays user input -- all Telegram API calls happen locally via Telethon. Your credentials never leave your machine.

**Local mode**: A Starlette web server starts on a random localhost port. The browser opens directly to `http://127.0.0.1:<port>`.

### Headless auth (Docker/SSH)

When no browser is available, use `curl`:

```bash
# URL is shown in server logs/error messages
# Step 1: Send OTP code
curl -X POST http://127.0.0.1:PORT/send-code

# Step 2: Verify OTP
curl -X POST http://127.0.0.1:PORT/verify -d '{"code":"12345"}'

# Step 3 (if 2FA): Submit password
curl -X POST http://127.0.0.1:PORT/verify -d '{"password":"your-2fa-password"}'
```

---

## Self-Hosting Auth Relay

By default, OTP authentication uses the hosted relay at `better-telegram-mcp.n24q02m.com`. To self-host:

```bash
# Build and run the auth relay server
cd auth-relay
docker build -t telegram-auth-relay .
docker run -d -p 8080:8080 --name telegram-auth-relay telegram-auth-relay
```

Then point your MCP server to your relay:

```json
{
  "env": {
    "TELEGRAM_AUTH_URL": "https://your-domain.com"
  }
}
```

Or use `TELEGRAM_AUTH_URL=local` for localhost-only mode (no remote relay needed).

---

## Security

### SSRF Protection

All user-provided URLs (media, auth relay) are validated against internal/private IP ranges. Blocked networks include: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, IPv6 link-local/ULA, and cloud metadata endpoints (`metadata.google.internal`). DNS resolution is checked to prevent SSRF via DNS rebinding (e.g., `127.0.0.1.nip.io`).

### Path Traversal Prevention

Local file paths (for media send/download) are validated:
- Blocks access to sensitive system directories: `/etc/`, `/proc/`, `/sys/`, `/dev/`, `/root/`, etc.
- Blocks access to hidden files/directories (dotfiles like `.ssh/`, `.env`)
- Output directories are validated separately with additional write-location restrictions (`/usr/`, `/bin/`, `/boot/`, etc.)

### Session File Security

- Session files stored with `600` permissions (owner read/write only)
- 2FA passwords are entered via web UI only -- never stored in environment variables
- Error messages are sanitized to prevent credential leakage

---

## Troubleshooting

| Error | Cause | Fix |
|:------|:------|:----|
| `No Telegram credentials found` | Neither bot token nor API credentials set | Set `TELEGRAM_BOT_TOKEN` or `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` |
| `Invalid bot token` | Token revoked or wrong | Regenerate via `/token` in [@BotFather](https://t.me/BotFather) |
| `not authenticated` | Session not yet authorized | Open the auth URL shown in error message (browser or curl) |
| `PhoneNumberInvalidError` | Wrong phone format | Include country code with `+` (e.g., `+84912345678`) |
| `SessionPasswordNeededError` | 2FA enabled | Enter 2FA password on the web auth page |
| `FloodWaitError` | Too many auth attempts | Wait the indicated seconds before retrying |
| `requires user mode` | Action not available in bot mode | Switch to user mode (API ID + Hash) |
| Session lost after Docker restart | Data volume not mounted | Add `-v ~/.better-telegram-mcp:/data` |
| OTP sent but where? | Code goes to Telegram app | Check the **Telegram app on your phone**, not SMS. Look for a message from "Telegram" |
| Headless auth? | No browser available | Use curl against the auth URL (see [Headless auth](#headless-auth-dockerssh)) |

---

## Build from Source

```bash
git clone https://github.com/n24q02m/better-telegram-mcp.git
cd better-telegram-mcp
uv sync --group dev
uv run ruff check .
uv run pytest
uv run better-telegram-mcp
```

### Docker Build

```bash
docker build -t n24q02m/better-telegram-mcp:latest .
```

**Requirements:** Python 3.13 (not 3.14+)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     MCP Client                          │
│          (Claude, Cursor, Copilot, Gemini CLI)          │
└────────────────────────┬────────────────────────────────┘
                         │ MCP Protocol (stdio)
                         v
┌─────────────────────────────────────────────────────────┐
│               better-telegram-mcp (FastMCP)             │
│                                                         │
│  ┌──────────┐ ┌──────┐ ┌───────┐ ┌────────┐            │
│  │ messages │ │chats │ │ media │ │contacts│ + config    │
│  │ 8 acts   │ │9 acts│ │5 acts │ │4 acts  │ + help     │
│  └────┬─────┘ └──┬───┘ └───┬───┘ └───┬────┘            │
│       │          │         │         │                  │
│       └──────────┴─────────┴─────────┘                  │
│                      │                                  │
│            ┌─────────┴──────────┐                       │
│            │  TelegramBackend   │  (ABC)                │
│            │   ┌────┐ ┌──────┐ │                        │
│            │   │Bot │ │ User │ │                        │
│            │   │API │ │MTProto│ │                        │
│            │   │httpx│ │Telethon│                        │
│            │   └────┘ └──────┘ │                        │
│            └────────────────────┘                        │
│                                                         │
│  Auth: AuthServer (Starlette, local)                    │
│     or AuthClient (httpx, polls remote relay)           │
│                                                         │
│  Security: validate_url, validate_file_path,            │
│            validate_output_dir                          │
└─────────────────────────────────────────────────────────┘
```

---

## Compatible With

[![Claude Desktop](https://img.shields.io/badge/Claude_Desktop-F9DC7C?logo=anthropic&logoColor=black)](#quick-start)
[![Claude Code](https://img.shields.io/badge/Claude_Code-000000?logo=anthropic&logoColor=white)](#quick-start)
[![Cursor](https://img.shields.io/badge/Cursor-000000?logo=cursor&logoColor=white)](#quick-start)
[![VS Code Copilot](https://img.shields.io/badge/VS_Code_Copilot-007ACC?logo=visualstudiocode&logoColor=white)](#quick-start)
[![Antigravity](https://img.shields.io/badge/Antigravity-4285F4?logo=google&logoColor=white)](#quick-start)
[![Gemini CLI](https://img.shields.io/badge/Gemini_CLI-8E75B2?logo=googlegemini&logoColor=white)](#quick-start)
[![OpenAI Codex](https://img.shields.io/badge/Codex-412991?logo=openai&logoColor=white)](#quick-start)
[![OpenCode](https://img.shields.io/badge/OpenCode-F7DF1E?logoColor=black)](#quick-start)

## Also by n24q02m

| Server | Description | Install |
|:-------|:------------|:--------|
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Notion API for AI agents | `npx -y @n24q02m/better-notion-mcp@latest` |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | Email (IMAP/SMTP) for AI agents | `npx -y @n24q02m/better-email-mcp@latest` |
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Web search, extraction, library docs | `uvx --python 3.13 wet-mcp@latest` |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search | `uvx mnemo-mcp@latest` |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Godot Engine for AI agents | `npx -y @n24q02m/better-godot-mcp@latest` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Privacy

See [PRIVACY.md](PRIVACY.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT - See [LICENSE](LICENSE).
