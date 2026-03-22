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
- **6 mega-tools** with action dispatch: `messages`, `chats`, `media`, `contacts`, `config`, `help`
- **Auto-detect mode** -- Set bot token for bot mode, or API credentials for user mode
- **Web-based OTP auth** -- Browser-based authentication with remote relay support for headless environments
- **Tool annotations** -- Each tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **MCP Resources** -- Documentation available as `telegram://docs/*` resources
- **Security hardened** -- SSRF protection, path traversal prevention, error sanitization

## Quick Start

### Claude Code Plugin (Recommended)

```bash
claude plugin add n24q02m/better-telegram-mcp
```

### MCP Server

> **Python 3.13 required** -- Python 3.14+ is **not** supported.

#### Bot Mode Setup

1. Open Telegram, search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, follow prompts to name your bot
3. Copy the token (format: `123456789:ABCdefGHI-JKLmnoPQRstUVwxyz`)

#### User Mode Setup

1. Go to [my.telegram.org](https://my.telegram.org), login with your phone number
2. Click "API development tools", create an app
3. Note your `api_id` (integer) and `api_hash` (32-char hex string)
4. On first run, a **local web page** opens for OTP authentication

#### Option 1: uvx

Bot mode:

```jsonc
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

```jsonc
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

#### Option 2: Docker

```jsonc
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

> For user mode in Docker, mount the session directory with `-v ~/.better-telegram-mcp:/data` so the session persists across container restarts.

## Tools

| Tool | Actions | Description |
|:-----|:--------|:------------|
| `messages` | `send`, `edit`, `delete`, `forward`, `pin`, `react`, `search`, `history` | Send, edit, delete, forward messages. Pin, react, search, browse history |
| `chats` | `list`, `info`, `create`, `join`, `leave`, `members`, `admin`, `settings`, `topics` | List and manage chats, groups, channels. Members, admin, forum topics |
| `media` | `send_photo`, `send_file`, `send_voice`, `send_video`, `download` | Send photos, files, voice notes, videos. Download media from messages |
| `contacts` | `list`, `search`, `add`, `block` | List, search, add contacts. Block/unblock users (user mode only) |
| `config` | `status`, `set`, `cache_clear` | Server status, update runtime settings, clear cache |
| `help` | -- | Full documentation for any tool |

### Mode Capabilities

| Feature | Bot | User |
|:--------|:---:|:----:|
| Send/Edit/Delete/Forward messages | Y | Y |
| Pin messages, React | Y | Y |
| Search messages, Browse history | -- | Y |
| List chats, Create groups/channels | -- | Y |
| Get chat info, Manage members | Y | Y |
| Send media (photo/file/voice/video) | Y | Y |
| Download media | -- | Y |
| Contacts (list/search/add/block) | -- | Y |

### MCP Resources

| URI | Content |
|:----|:--------|
| `telegram://docs/messages` | Message operations reference |
| `telegram://docs/chats` | Chat management reference |
| `telegram://docs/media` | Media send/download reference |
| `telegram://docs/contacts` | Contact management reference |
| `telegram://stats` | All documentation combined |

## Configuration

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Bot mode | -- | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_ID` | User mode | -- | API ID from [my.telegram.org](https://my.telegram.org) (integer) |
| `TELEGRAM_API_HASH` | User mode | -- | API hash from [my.telegram.org](https://my.telegram.org) (32-char hex) |
| `TELEGRAM_PHONE` | User mode | -- | Phone number with country code (e.g., `+84912345678`) |
| `TELEGRAM_AUTH_URL` | No | `https://better-telegram-mcp.n24q02m.com` | Auth relay URL. Set `local` for localhost-only mode |
| `TELEGRAM_SESSION_NAME` | No | `default` | Session file name (useful for multiple accounts) |
| `TELEGRAM_DATA_DIR` | No | `~/.better-telegram-mcp` | Data directory for session files |

**Mode detection**: If `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` are set, user mode is used. Otherwise, `TELEGRAM_BOT_TOKEN` is used. No silent fallback -- if neither is set, the server exits with an error.

### Auth Flow (User Mode Only)

1. On first run, a **web-based auth UI** opens in your browser (or URL is logged for headless)
2. Click "Send OTP Code" -- code is sent to the **Telegram app** (not SMS)
3. Enter the OTP code; if 2FA is enabled, enter your password
4. Session file is saved at `~/.better-telegram-mcp/<name>.session` (600 permissions)
5. Tools become active immediately -- no restart needed

| Auth Mode | `TELEGRAM_AUTH_URL` | Use case |
|:----------|:--------------------|:---------|
| **Remote** (default) | `https://better-telegram-mcp.n24q02m.com` | Headless, SSH, Docker |
| **Self-hosted** | `https://your-domain.com` | Custom relay deployment |
| **Local** | `local` | Desktop, offline |

**Headless auth (Docker/SSH)** -- use `curl` against the auth URL shown in logs:

```bash
curl -X POST http://127.0.0.1:PORT/send-code
curl -X POST http://127.0.0.1:PORT/verify -d '{"code":"12345"}'
curl -X POST http://127.0.0.1:PORT/verify -d '{"password":"your-2fa-password"}'  # if 2FA
```

### Security

- **SSRF Protection** -- All URLs validated against internal/private IP ranges, DNS rebinding blocked
- **Path Traversal Prevention** -- File paths validated, sensitive directories blocked
- **Session File Security** -- 600 permissions, 2FA via web UI only (never stored in env vars)
- **Error Sanitization** -- Credentials never leaked in error messages

## Build from Source

```bash
git clone https://github.com/n24q02m/better-telegram-mcp.git
cd better-telegram-mcp
uv sync
uv run better-telegram-mcp
```

## Compatible With

[![Claude Code](https://img.shields.io/badge/Claude_Code-000000?logo=anthropic&logoColor=white)](#quick-start)
[![Claude Desktop](https://img.shields.io/badge/Claude_Desktop-F9DC7C?logo=anthropic&logoColor=black)](#quick-start)
[![Cursor](https://img.shields.io/badge/Cursor-000000?logo=cursor&logoColor=white)](#quick-start)
[![VS Code Copilot](https://img.shields.io/badge/VS_Code_Copilot-007ACC?logo=visualstudiocode&logoColor=white)](#quick-start)
[![Antigravity](https://img.shields.io/badge/Antigravity-4285F4?logo=google&logoColor=white)](#quick-start)
[![Gemini CLI](https://img.shields.io/badge/Gemini_CLI-8E75B2?logo=googlegemini&logoColor=white)](#quick-start)
[![OpenAI Codex](https://img.shields.io/badge/Codex-412991?logo=openai&logoColor=white)](#quick-start)
[![OpenCode](https://img.shields.io/badge/OpenCode-F7DF1E?logoColor=black)](#quick-start)

## Also by n24q02m

| Server | Description |
|:-------|:------------|
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Web search, content extraction, library docs & multimodal analysis |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search and embedded sync |
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Enhanced Notion API integration with 9 composite tools |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | Email management via IMAP/SMTP |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Godot Engine for AI agents |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT -- See [LICENSE](LICENSE).
