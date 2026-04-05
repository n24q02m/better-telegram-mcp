# Better Telegram MCP -- Manual Setup Guide

## Prerequisites

- **Python 3.13** (3.14+ is NOT supported)
- `uv` or `uvx` installed ([docs](https://docs.astral.sh/uv/getting-started/installation/))
- Docker (optional, for containerized setup)
- A Telegram account and either a bot token or API credentials

## Method 1: Plugin Install

For Claude Code users, the plugin approach is the simplest.

1. Open Claude Code
2. Run the following commands:
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install better-telegram-mcp@n24q02m-plugins
   ```
3. The server starts automatically when Claude Code launches
4. On first run, a relay setup URL appears -- open it to configure credentials

## Method 2: uvx Direct

1. Add to your MCP client configuration file:

   **Claude Code** (`~/.claude/settings.local.json`):
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

   **Codex CLI** (`~/.codex/config.toml`):
   ```toml
   [mcp_servers.telegram]
   command = "uvx"
   args = ["--python", "3.13", "better-telegram-mcp"]
   ```

   **OpenCode** (`opencode.json` in project root):
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

2. Restart your MCP client
3. A relay setup URL appears -- configure credentials via the web UI

## Method 3: Docker

### Bot Mode

1. Pull the image:
   ```bash
   docker pull n24q02m/better-telegram-mcp:latest
   ```

2. Run with bot token:
   ```bash
   docker run -i --rm \
     -e TELEGRAM_BOT_TOKEN=your_bot_token \
     -v telegram-data:/data \
     n24q02m/better-telegram-mcp
   ```

### User Mode

1. Run with API credentials:
   ```bash
   docker run -i --rm \
     -e TELEGRAM_API_ID=your_api_id \
     -e TELEGRAM_API_HASH=your_api_hash \
     -e TELEGRAM_PHONE=+84912345678 \
     -v ~/.better-telegram-mcp:/data \
     n24q02m/better-telegram-mcp
   ```

2. Mount `~/.better-telegram-mcp:/data` so session files persist

### MCP Client Config (Docker)

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

## Method 4: HTTP Remote (Multi-User)

For shared deployments with multiple users:

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

This requires deploying the HTTP transport separately.

## Method 5: Build from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/n24q02m/better-telegram-mcp.git
   cd better-telegram-mcp
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run the server:
   ```bash
   uv run better-telegram-mcp
   ```

## Credential Setup

### Bot Mode

1. Open Telegram, search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, follow prompts to name your bot
3. Copy the token (format: `123456789:ABCdefGHI-JKLmnoPQRstUVwxyz`)
4. Set the token:
   ```bash
   export TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
   ```

### User Mode

1. Go to [my.telegram.org](https://my.telegram.org), login with your phone number
2. Click "API development tools", create an app
3. Note your `api_id` (integer) and `api_hash` (32-char hex string)
4. Set the credentials:
   ```bash
   export TELEGRAM_API_ID=12345678
   export TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
   export TELEGRAM_PHONE=+84912345678
   ```

### User Mode OTP Authentication

On first run with user mode credentials:

1. A web-based auth UI opens in your browser
2. Click "Send OTP Code" -- code is sent to the **Telegram app** (not SMS)
3. Enter the OTP code
4. If 2FA is enabled, enter your password (never stored anywhere)
5. Session file is saved at `~/.better-telegram-mcp/<name>.session` (600 permissions)
6. Subsequent runs use the session file -- no re-authentication needed

**Headless environments (SSH/Docker):** The auth URL is logged to stderr. Use curl:

```bash
curl -X POST http://127.0.0.1:PORT/send-code
curl -X POST http://127.0.0.1:PORT/verify -d '{"code":"12345"}'
curl -X POST http://127.0.0.1:PORT/verify -d '{"password":"your-2fa-password"}'  # if 2FA
```

### Zero-Config Relay (BETA)

> **Note**: Relay is a **BETA** credential provisioning flow. For stable production use, prefer environment variables. The relay blocks server startup on first run and may time out in some MCP clients.

Instead of setting environment variables, you can use the web relay:

1. Start the server without any credentials set
2. A setup URL appears in stderr
3. Open the URL and choose mode (Bot or User)
4. Fill in credentials on the guided form
5. Credentials are encrypted and stored at `~/.config/mcp/config.enc`

## Environment Variable Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Bot mode | -- | Bot token from @BotFather |
| `TELEGRAM_API_ID` | User mode | -- | API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | User mode | -- | API hash from my.telegram.org |
| `TELEGRAM_PHONE` | User mode | -- | Phone with country code |
| `TELEGRAM_AUTH_URL` | No | `https://better-telegram-mcp.n24q02m.com` | Auth relay URL. `local` for localhost |
| `TELEGRAM_SESSION_NAME` | No | `default` | Session file name |
| `TELEGRAM_DATA_DIR` | No | `~/.better-telegram-mcp` | Data directory |

### Mode Detection

- `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` set: **User mode**
- Only `TELEGRAM_BOT_TOKEN` set: **Bot mode**
- Neither set: relay setup page opens

### Auth URL Modes

| `TELEGRAM_AUTH_URL` | Behavior |
|:--------------------|:---------|
| `https://better-telegram-mcp.n24q02m.com` (default) | Remote relay, works in headless/SSH/Docker |
| `https://your-domain.com` | Self-hosted relay |
| `local` | Local web server on localhost |

## Troubleshooting

### Bot cannot send messages

Bots can only message users who have started a conversation with the bot first. Have the target user send `/start` to your bot.

### OTP code not received

The OTP code is sent to the **Telegram app** as a message from "Telegram" service notifications, not via SMS. Check your Telegram app.

### Session expired / authentication required

Delete the session file and re-authenticate:

```bash
rm ~/.better-telegram-mcp/default.session
```

Then restart the server.

### Docker user mode session not persisted

Mount the data directory to persist sessions:

```bash
docker run -i --rm \
  -v ~/.better-telegram-mcp:/data \
  ...
```

### 2FA password prompt

2FA passwords are entered via the web UI during OTP authentication. They are never stored in environment variables or files.

### "FloodWaitError" from Telegram

Telegram rate-limits API calls. Wait the indicated time before retrying. The server handles this automatically for most operations.

### Relay setup URL does not appear

The relay URL only appears when no credentials are set. If you have `TELEGRAM_BOT_TOKEN` or `TELEGRAM_API_ID`+`TELEGRAM_API_HASH` set, the relay is skipped.
