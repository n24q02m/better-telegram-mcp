# better-telegram-mcp

[![PyPI](https://img.shields.io/pypi/v/better-telegram-mcp)](https://pypi.org/project/better-telegram-mcp/)
[![Docker](https://img.shields.io/docker/v/n24q02m/better-telegram-mcp?label=docker)](https://hub.docker.com/r/n24q02m/better-telegram-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue)](https://modelcontextprotocol.io/servers/io.github.n24q02m%2Fbetter-telegram-mcp)
[![Glama](https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp/badge)](https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp)
[![Codecov](https://codecov.io/gh/n24q02m/better-telegram-mcp/graph/badge.svg)](https://codecov.io/gh/n24q02m/better-telegram-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

Get a bot token from [@BotFather](https://t.me/BotFather), then:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF uvx --python 3.13 better-telegram-mcp
```

### User Mode

Get API credentials from [my.telegram.org](https://my.telegram.org), then:

```bash
export TELEGRAM_API_ID=12345
export TELEGRAM_API_HASH=abcdef123456

# Authenticate once (interactive)
uvx --python 3.13 better-telegram-mcp auth

# Run the server
uvx --python 3.13 better-telegram-mcp
```

## Configuration

All configuration is via environment variables with `TELEGRAM_` prefix:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot mode | Bot token from @BotFather |
| `TELEGRAM_API_ID` | User mode | API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | User mode | API hash from my.telegram.org |
| `TELEGRAM_PHONE` | User mode (auth) | Phone number for authentication |
| `TELEGRAM_PASSWORD` | No | 2FA password (if enabled) |
| `TELEGRAM_SESSION_NAME` | No | Session file name (default: `default`) |
| `TELEGRAM_DATA_DIR` | No | Data directory (default: `~/.better-telegram-mcp`) |

## MCP Config Examples

### Claude Code

```bash
claude mcp add telegram -- env TELEGRAM_BOT_TOKEN=123456:ABC-DEF uvx --python 3.13 better-telegram-mcp
```

### Claude Desktop

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

### Cursor

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
docker run -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF n24q02m/better-telegram-mcp

# User mode (mount session data)
docker run -e TELEGRAM_API_ID=12345 -e TELEGRAM_API_HASH=abcdef123456 \
  -v ~/.better-telegram-mcp:/data \
  n24q02m/better-telegram-mcp
```

Docker config for Claude Desktop:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TELEGRAM_BOT_TOKEN=123456:ABC-DEF",
        "n24q02m/better-telegram-mcp"
      ]
    }
  }
}
```

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
| Forum topics | Y | Y |
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

## Compatible With

- [Claude Code](https://claude.com/claude-code)
- [Claude Desktop](https://claude.ai/download)
- [Cursor](https://cursor.sh)
- [VS Code Copilot](https://code.visualstudio.com/docs/copilot)
- Any MCP-compatible client

## License

MIT
