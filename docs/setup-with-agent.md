# Better Telegram MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up better-telegram-mcp.

## Option 1: Claude Code Plugin (Recommended)

```bash
# Install from marketplace (includes skills: /setup-bot, /channel-post)
/plugin marketplace add n24q02m/claude-plugins
/plugin install better-telegram-mcp@n24q02m-plugins
```

You still need to provide credentials (bot token or user API credentials). See the Authentication section below.

## Option 2: MCP Direct

**Python 3.13 required** -- Python 3.14+ is NOT supported.

### Claude Code (settings.json)

Add to `~/.claude/settings.local.json` under `"mcpServers"`:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uvx",
      "args": ["--python", "3.13", "better-telegram-mcp"]
    }
  }
}
```

### Codex CLI (config.toml)

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.telegram]
command = "uvx"
args = ["--python", "3.13", "better-telegram-mcp"]
```

### OpenCode (opencode.json)

Add to `opencode.json` in the project root:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uvx",
      "args": ["--python", "3.13", "better-telegram-mcp"]
    }
  }
}
```

## Option 3: Docker

### Bot Mode

```bash
docker run -i --rm \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -v telegram-data:/data \
  n24q02m/better-telegram-mcp
```

### User Mode

```bash
docker run -i --rm \
  -e TELEGRAM_API_ID=your_api_id \
  -e TELEGRAM_API_HASH=your_api_hash \
  -e TELEGRAM_PHONE=+84912345678 \
  -v ~/.better-telegram-mcp:/data \
  n24q02m/better-telegram-mcp
```

Mount `~/.better-telegram-mcp:/data` so session files persist across container restarts.

Or as an MCP server config:

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
      ]
    }
  }
}
```

## Option 4: HTTP Remote (Multi-User Deployment)

For shared/multi-user deployments, the server can run as an HTTP endpoint with bearer token authentication and Dynamic Client Registration (DCR).

```json
{
  "mcpServers": {
    "telegram": {
      "url": "https://your-domain.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_ACCESS_TOKEN"
      }
    }
  }
}
```

HTTP mode requires a separate deployment. See the [HTTP transport source](../src/better_telegram_mcp/transports/) for details.

## Environment Variables

### Core Credentials (One Mode Required)

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Bot mode | -- | Bot token from [@BotFather](https://t.me/BotFather) (format: `123456789:ABCdef...`) |
| `TELEGRAM_API_ID` | User mode | -- | API ID from [my.telegram.org](https://my.telegram.org) (integer) |
| `TELEGRAM_API_HASH` | User mode | -- | API hash from [my.telegram.org](https://my.telegram.org) (32-char hex) |
| `TELEGRAM_PHONE` | User mode | -- | Phone number with country code (e.g., `+84912345678`) |

### Auth and Session

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_AUTH_URL` | No | `https://better-telegram-mcp.n24q02m.com` | Auth relay URL. Set `local` for localhost-only mode |
| `TELEGRAM_SESSION_NAME` | No | `default` | Session file name (useful for multiple accounts) |
| `TELEGRAM_DATA_DIR` | No | `~/.better-telegram-mcp` | Data directory for session files |

### Mode Detection

- If `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` are set: **User mode** (MTProto via Telethon)
- If only `TELEGRAM_BOT_TOKEN` is set: **Bot mode** (HTTP via Bot API)
- If neither is set: server shows relay setup page for configuration

## Authentication

### Zero-Config Relay

> **Recommended.** The relay is the primary setup method. Credentials are encrypted end-to-end and stored locally. Environment variables are supported for backward compatibility.

On first run without any credentials in environment:

1. Server starts and creates a relay session
2. A setup URL is printed to stderr
3. Open the URL in any browser
4. Choose mode (Bot or User) and fill in credentials
5. Credentials are encrypted and stored locally at `~/.config/mcp/config.enc`
6. Subsequent runs load saved credentials automatically

The relay form has 2 modes:

**Bot Mode:**
- **Bot Token** -- from @BotFather on Telegram

**User Mode:**
- **Phone Number** -- with country code

### User Mode OTP Authentication

After credentials are configured (via relay or environment variables), user mode requires OTP verification on first run:

1. A web-based auth UI opens in your browser (or URL is logged for headless)
2. Click "Send OTP Code" -- code is sent to the Telegram app (not SMS)
3. Enter the OTP code
4. If 2FA is enabled, enter your password (never stored in environment)
5. Session file is saved at `~/.better-telegram-mcp/<name>.session` (600 permissions)
6. Tools become active immediately -- no restart needed

Auth modes:

| Mode | `TELEGRAM_AUTH_URL` | Use case |
|:-----|:--------------------|:---------|
| **Remote** (default) | `https://better-telegram-mcp.n24q02m.com` | Headless, SSH, Docker |
| **Self-hosted** | `https://your-domain.com` | Custom relay deployment |
| **Local** | `local` | Desktop, offline |

### Environment Variables (Recommended)

Set credentials directly as environment variables to skip relay entirely.

## Mode Capabilities

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

## Verification

After setup, verify the server is working by calling the `config` tool:

```
config(action="status")
```

Expected: returns server status including mode (bot/user), connection state, and session info.

Then test sending a message:

```
message(action="send", chat_id="me", text="Hello from MCP!")
```

Note: In bot mode, the bot can only message users who have started a conversation with it.
