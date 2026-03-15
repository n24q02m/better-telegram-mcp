# better-telegram-mcp

[![CI](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/n24q02m/better-telegram-mcp/graph/badge.svg)](https://codecov.io/gh/n24q02m/better-telegram-mcp)
[![PyPI](https://img.shields.io/pypi/v/better-telegram-mcp?logo=pypi&logoColor=white)](https://pypi.org/project/better-telegram-mcp/)
[![Docker](https://img.shields.io/docker/v/n24q02m/better-telegram-mcp?label=docker&logo=docker&logoColor=white&sort=semver)](https://hub.docker.com/r/n24q02m/better-telegram-mcp)
[![License: MIT](https://img.shields.io/github/license/n24q02m/better-telegram-mcp)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot_API_+_MTProto-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue)](https://modelcontextprotocol.io/servers/io.github.n24q02m%2Fbetter-telegram-mcp)
[![Glama](https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp/badge)](https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp)
[![semantic-release](https://img.shields.io/badge/semantic--release-e10079?logo=semantic-release&logoColor=white)](https://github.com/semantic-release/semantic-release)
[![Renovate](https://img.shields.io/badge/renovate-enabled-1A1F6C?logo=renovatebot&logoColor=white)](https://github.com/renovatebot/renovate)

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

1. Go to [https://my.telegram.org](https://my.telegram.org)
2. Login with your phone number (OTP sent via Telegram, not SMS)
3. Click "API development tools"
4. Create an app, note `api_id` (integer) and `api_hash` (32-char hex)
5. Authenticate once, then run:

```bash
export TELEGRAM_API_ID=12345
export TELEGRAM_API_HASH=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4

# Step 1: Authenticate (interactive, one-time)
uvx --python 3.13 better-telegram-mcp auth

# Step 2: Run the server
uvx --python 3.13 better-telegram-mcp
```

## Auth CLI

The `auth` command creates a Telethon session file for user mode. This must be done once before using user mode.

```bash
# Basic auth (prompts for phone + OTP)
TELEGRAM_API_ID=... TELEGRAM_API_HASH=... uvx --python 3.13 better-telegram-mcp auth

# With phone number pre-set (only prompts for OTP)
TELEGRAM_API_ID=... TELEGRAM_API_HASH=... TELEGRAM_PHONE=+84912345678 \
  uvx --python 3.13 better-telegram-mcp auth

# With 2FA password pre-set
TELEGRAM_API_ID=... TELEGRAM_API_HASH=... TELEGRAM_PASSWORD=my2fapass \
  uvx --python 3.13 better-telegram-mcp auth

# Named session (for multiple accounts)
TELEGRAM_API_ID=... TELEGRAM_API_HASH=... \
  uvx --python 3.13 better-telegram-mcp auth --session-name work
```

**Session file**: Stored at `~/.better-telegram-mcp/<name>.session` with `600` permissions (owner-only). Treat this file like a password.

**2FA handling**: If your account has Two-Step Verification enabled, set `TELEGRAM_PASSWORD` env var or enter it interactively when prompted.

## Configuration

All configuration is via environment variables with `TELEGRAM_` prefix:

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot mode | - | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_ID` | User mode | - | API ID from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_API_HASH` | User mode | - | API hash from [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_PHONE` | No | Interactive prompt | Phone number for auth (e.g., `+84912345678`) |
| `TELEGRAM_PASSWORD` | No | Interactive prompt | 2FA password (if enabled) |
| `TELEGRAM_SESSION_NAME` | No | `default` | Session file name (for multiple accounts) |
| `TELEGRAM_DATA_DIR` | No | `~/.better-telegram-mcp` | Data directory for session files |

**Mode detection**: If `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` are set, user mode is used (priority). Otherwise, `TELEGRAM_BOT_TOKEN` is used for bot mode. No silent fallback between modes.

## MCP Config Examples

### Claude Code

```bash
# Bot mode
claude mcp add telegram -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF -- uvx --python 3.13 better-telegram-mcp

# User mode (after running auth)
claude mcp add telegram -e TELEGRAM_API_ID=12345 -e TELEGRAM_API_HASH=abc123 -- uvx --python 3.13 better-telegram-mcp
```

### Claude Desktop / Cursor

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

# User mode (auth must be done on host first, then mount session)
docker run -i --rm \
  -e TELEGRAM_API_ID=12345 \
  -e TELEGRAM_API_HASH=abcdef123456 \
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

**Note**: For user mode in Docker, authenticate on the host first (`uvx better-telegram-mcp auth`), then mount the session directory with `-v ~/.better-telegram-mcp:/data`.

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
| `Session not authorized` | Session file missing or expired | Run `uvx better-telegram-mcp auth` |
| `PhoneNumberInvalidError` | Wrong phone format | Include country code with `+` (e.g., `+84912345678`) |
| `SessionPasswordNeededError` | 2FA enabled | Set `TELEGRAM_PASSWORD` env or enter interactively |
| `FloodWaitError` | Too many auth attempts | Wait the indicated seconds |
| `requires user mode` | Action not available in bot mode | Switch to user mode (API ID + Hash) |
| Session lost after Docker restart | Data volume not mounted | Add `-v ~/.better-telegram-mcp:/data` |

## Compatible With

[![Claude Desktop](https://img.shields.io/badge/Claude_Desktop-F9DC7C?logo=anthropic&logoColor=black)](https://claude.ai/download)
[![Claude Code](https://img.shields.io/badge/Claude_Code-000000?logo=anthropic&logoColor=white)](https://claude.com/claude-code)
[![Cursor](https://img.shields.io/badge/Cursor-000000?logo=cursor&logoColor=white)](https://cursor.sh)
[![VS Code Copilot](https://img.shields.io/badge/VS_Code_Copilot-007ACC?logo=visualstudiocode&logoColor=white)](https://code.visualstudio.com)
[![Antigravity](https://img.shields.io/badge/Antigravity-4285F4?logo=google&logoColor=white)](https://cloud.google.com/products/gemini)
[![Gemini CLI](https://img.shields.io/badge/Gemini_CLI-8E75B2?logo=googlegemini&logoColor=white)](https://github.com/google-gemini/gemini-cli)
[![OpenAI Codex](https://img.shields.io/badge/Codex-412991?logo=openai&logoColor=white)](https://github.com/openai/codex)
[![OpenCode](https://img.shields.io/badge/OpenCode-F7DF1E?logoColor=black)](https://github.com/opencode-ai/opencode)

## Also by n24q02m

| Server | Description | Install |
|---|---|---|
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Notion API for AI agents | `npx -y @n24q02m/better-notion-mcp@latest` |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | Email (IMAP/SMTP) for AI agents | `npx -y @n24q02m/better-email-mcp@latest` |
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Web search, extraction, library docs | `uvx --python 3.13 wet-mcp@latest` |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory | `uvx mnemo-mcp@latest` |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Godot Engine for AI agents | `npx -y @n24q02m/better-godot-mcp@latest` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - See [LICENSE](LICENSE).
