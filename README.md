# better-telegram-mcp

mcp-name: io.github.n24q02m/better-telegram-mcp

[![CI](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/n24q02m/better-telegram-mcp/graph/badge.svg?token=d0fef60a-542e-4be2-9528-6e3a12931067)](https://codecov.io/gh/n24q02m/better-telegram-mcp)
[![PyPI](https://img.shields.io/pypi/v/better-telegram-mcp?logo=pypi&logoColor=white)](https://pypi.org/project/better-telegram-mcp/)
[![Docker](https://img.shields.io/docker/v/n24q02m/better-telegram-mcp?label=docker&logo=docker&logoColor=white&sort=semver)](https://hub.docker.com/r/n24q02m/better-telegram-mcp)
[![License: MIT](https://img.shields.io/github/license/n24q02m/better-telegram-mcp)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot_API_+_MTProto-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org)
[![MCP](https://img.shields.io/badge/MCP-000000?logo=anthropic&logoColor=white)](#)
[![semantic-release](https://img.shields.io/badge/semantic--release-e10079?logo=semantic-release&logoColor=white)](https://github.com/python-semantic-release/python-semantic-release)
[![Renovate](https://img.shields.io/badge/renovate-enabled-1A1F6C?logo=renovatebot&logoColor=white)](https://github.com/renovatebot/renovate)

<a href="https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp/badge" alt="better-telegram-mcp MCP server" />
</a>

Production-grade MCP server for Telegram with dual-mode support: Bot API (via httpx) for quick bot integrations and MTProto (via Telethon) for full user-account access including message search, history browsing, contact management, and group creation.

## Features

- **6 mega-tools** with action dispatch: `messages`, `chats`, `media`, `contacts`, `config`, `help`
- **Dual mode**: Bot API (httpx) for bots, MTProto (Telethon) for user accounts
- **3-tier token optimization**: Only 6 tools registered instead of 30+ individual endpoints
- **Tool annotations**: Each tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **MCP Resources**: Documentation available as `telegram://docs/*` resources
- **Auto-detect mode**: Set bot token for bot mode, or API credentials for user mode

## Quick Start

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
4. Add to your MCP config with all required env vars (see examples below)
5. Start using — on first run, a **local web page** opens in your browser for OTP authentication:
   - Click "Send OTP Code" to receive a code in your **Telegram app**
   - Enter the OTP code on the web page
   - If 2FA is enabled, enter your password on the same page
   - Headless (Docker/SSH): use `curl` to hit the same endpoints (URL shown in logs/error messages)
6. Done — session file persists at `~/.better-telegram-mcp/<name>.session`, no more auth needed on subsequent runs

> **Security**: The session file has `600` permissions (owner-only). Treat it like a password — anyone with this file can access your Telegram account.

## Configuration

All configuration is via environment variables with `TELEGRAM_` prefix:

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot mode | - | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_ID` | User mode | - | API ID from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_API_HASH` | User mode | - | API hash from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_PHONE` | User mode | - | Phone number with country code (e.g., `+84912345678`). Required for web auth UI. |
| `TELEGRAM_AUTH_URL` | No | `https://better-telegram-mcp.n24q02m.com` | Auth server URL. Use `local` for localhost mode, or a custom URL for self-hosted relay. |
| `TELEGRAM_SESSION_NAME` | No | `default` | Session file name (for multiple accounts) |
| `TELEGRAM_DATA_DIR` | No | `~/.better-telegram-mcp` | Data directory for session files |

**Mode detection**: If `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` are set, user mode is used (priority). Otherwise, `TELEGRAM_BOT_TOKEN` is used for bot mode. No silent fallback between modes.

## MCP Config Examples

### Claude Code

```bash
# Bot mode
claude mcp add telegram -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF -- uvx --python 3.13 better-telegram-mcp

# User mode (auto-auth on first run)
claude mcp add telegram -e TELEGRAM_API_ID=12345 -e TELEGRAM_API_HASH=abc123 -e TELEGRAM_PHONE=+1234567890 -- uvx --python 3.13 better-telegram-mcp
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

## Docker

```bash
# Bot mode
docker run -i --rm -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF n24q02m/better-telegram-mcp

# User mode (auto-auth on first run, mount session dir for persistence)
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
        "n24q02m/better-telegram-mcp"
      ],
      "env": {
        "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"
      }
    }
  }
}
```

**Note**: For user mode in Docker, mount the session directory with `-v ~/.better-telegram-mcp:/data` so the session persists across container restarts. On first run, the auth web server starts on localhost — use port mapping (`-p 8080:PORT`) or `curl` to complete auth.

## Mode Capabilities

| Feature | Bot Mode | User Mode |
|---|:---:|:---:|
| Send messages | Y | Y |
| Edit messages | Y | Y |
| Delete messages | Y | Y |
| Forward messages | Y | Y |
| Pin messages | Y | Y |
| React to messages | Y | Y |
| Search messages | - | Y |
| Browse history | - | Y |
| List chats | - | Y |
| Get chat info | Y | Y |
| Create groups/channels | - | Y |
| Join/Leave chats | Partial | Y |
| Manage members | Y | Y |
| Admin promotion | Y | Y |
| Chat settings | Y | Y |
| Forum topics | Partial | Y |
| Send media (photo/file/voice/video) | Y | Y |
| Download media | - | Y |
| List contacts | - | Y |
| Search contacts | - | Y |
| Add contacts | - | Y |
| Block/Unblock users | - | Y |

## Tool Reference

Use the `help` tool for full documentation:

```
help(topic="messages")  # Message operations
help(topic="chats")     # Chat management
help(topic="media")     # Media send/download
help(topic="contacts")  # Contact management
help(topic="all")       # Everything
```

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `No Telegram credentials found` | Neither bot token nor API credentials set | Set `TELEGRAM_BOT_TOKEN` or `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` |
| `Invalid bot token` | Token revoked or wrong | Regenerate via `/token` in [@BotFather](https://t.me/BotFather) |
| `not authenticated` | Session not yet authorized | Open the auth URL shown in error message (browser or curl) |
| `PhoneNumberInvalidError` | Wrong phone format | Include country code with `+` (e.g., `+84912345678`) |
| `SessionPasswordNeededError` | 2FA enabled | Enter 2FA password on the web auth page |
| `FloodWaitError` | Too many auth attempts | Wait the indicated seconds before retrying |
| `requires user mode` | Action not available in bot mode | Switch to user mode (API ID + Hash) |
| Session lost after Docker restart | Data volume not mounted | Add `-v ~/.better-telegram-mcp:/data` |
| OTP sent but where? | Code goes to Telegram app | Check the **Telegram app on your phone** (not SMS). Look for a message from "Telegram" with a login code. |
| Headless auth? | No browser available | Use curl: `curl -X POST http://127.0.0.1:PORT/send-code` then `curl -X POST http://127.0.0.1:PORT/verify -d '{"code":"12345"}'` |

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
|---|---|---|
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Notion API for AI agents | `npx -y @n24q02m/better-notion-mcp@latest` |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | Email (IMAP/SMTP) for AI agents | `npx -y @n24q02m/better-email-mcp@latest` |
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Web search, extraction, library docs | `uvx --python 3.13 wet-mcp@latest` |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search | `uvx mnemo-mcp@latest` |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Godot Engine for AI agents | `npx -y @n24q02m/better-godot-mcp@latest` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - See [LICENSE](LICENSE).

