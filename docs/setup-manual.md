# Better Telegram MCP -- Manual Setup Guide

> **2026-05-02 Update (v&lt;auto&gt;+)**: Plugin install (Method 1) uses stdio mode with `TELEGRAM_BOT_TOKEN`. Bot mode only.
> User mode (MTProto via phone+OTP) is HTTP-only after this update.
> Set `TELEGRAM_BOT_TOKEN` in plugin config (Method 1), or switch to HTTP mode for user mode.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, no OAuth/HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx/npx hits PATH or Python version issues. |
| **3. Recommended** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-device, OAuth/relay-form auth, team self-host, claude.ai web compatibility. |

All MCP servers across this stack share this priority hierarchy. Note: 2 plugins (`better-godot-mcp` and `better-code-review-graph`) only support Method 1 (stdio) -- they need direct host access to project files / repo paths and don't ship Docker / HTTP variants.

## Prerequisites

- **Python 3.13** (3.14+ is NOT supported)
- `uv` or `uvx` installed ([docs](https://docs.astral.sh/uv/getting-started/installation/))
- Docker (optional, for self-hosted HTTP setup)
- A Telegram account and either a bot token (bot mode) or a phone number (user mode, HTTP only)

## Method 1: Plugin Install (stdio, Bot Mode Only)

For Claude Code users, the plugin approach is the simplest. **Bot mode only** -- user mode requires HTTP (see Method 3).

1. Get a bot token from [@BotFather](https://t.me/BotFather):
   - Open Telegram, send `/newbot` to @BotFather
   - Follow prompts to name your bot
   - Copy the token (format: `123456789:ABCdefGHI-JKLmnoPQRstUVwxyz`)

2. Open Claude Code and install the plugin:
   ```bash
   /plugin marketplace add n24q02m/claude-plugins
   /plugin install better-telegram-mcp@n24q02m-plugins
   ```

3. Configure `TELEGRAM_BOT_TOKEN` in the plugin settings (Claude Code prompts on first use), or set the env var system-wide:
   ```bash
   export TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
   ```

4. Restart Claude Code -- the server starts in stdio bot mode.

> **Need user mode (read messages, browse chats, manage groups)?** Bot tokens cannot do this. Skip to Method 3 (HTTP) -- user mode runs over HTTP only.

## Method 2: Docker stdio (fallback)

1. Pull the image:
   ```bash
   docker pull n24q02m/better-telegram-mcp:latest
   ```

2. Run with bot token:
   ```bash
   docker run -i --rm \
     -e TELEGRAM_BOT_TOKEN=your_bot_token \
     n24q02m/better-telegram-mcp
   ```

### MCP Client Config (Docker)

```json
{
  "mcpServers": {
    "telegram": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TELEGRAM_BOT_TOKEN",
        "n24q02m/better-telegram-mcp"
      ]
    }
  }
}
```

> Docker stdio supports bot mode only. For user mode, run the container in HTTP mode (see Method 3 self-host).

## Why upgrade to HTTP mode?

Stdio (Methods 1-2) is the simplest path for **bot mode**, but stdio cannot host the browser-based phone+OTP flow that **user mode** requires. Switch to HTTP for any of these reasons:

- **User mode access** (REQUIRED for user mode) -- read messages, browse chat history, list contacts, create groups/channels. Bot tokens cannot do this; only MTProto user sessions can. User mode auth is browser-based (phone + OTP code from Telegram app + optional 2FA password) and only HTTP transport hosts that flow.
- **claude.ai web compatibility** -- claude.ai supports HTTP MCP servers; stdio is desktop/CLI only.
- **One server, many sessions** -- a single HTTP server is shared across N Claude Code sessions instead of one stdio process per session.
- **Multi-device cred sync** -- log in once on any device; the server keeps the session.
- **Multi-user team sharing** -- HTTP supports per-JWT-sub credential isolation, so a team can share one self-hosted instance.
- **Always-on persistent process** -- enables webhook listeners, long-running agents, and scheduled tasks.

## Method 3: Docker HTTP (recommended)

### 3.1. Hosted (n24q02m.com)

Live production endpoint (Dynamic Client Registration + relay form auth):

```json
{
  "mcpServers": {
    "telegram": {
      "url": "https://better-telegram-mcp.n24q02m.com/mcp"
    }
  }
}
```

The client registers a public DCR client at `/register`, then opens
`/authorize` to fill the Telegram relay form. The form supports both modes:

- **Bot mode** -- paste your bot token from [@BotFather](https://t.me/BotFather)
- **User mode** -- enter your phone number, then the OTP code Telegram sends to your Telegram app, then your 2FA password if enabled

The server bundles public Telegram dev credentials (`api_id` and `api_hash`), so users do not need to register at [my.telegram.org](https://my.telegram.org). After the form completes, the server issues a Bearer JWT and tools become active immediately.

> Python 3.14+ is **not supported** because Telethon and `cryptg` have not yet shipped 3.14 wheels. The Docker image bakes in Python 3.13.

### 3.2. Self-host with docker-compose

For private deployments (single user or team):

1. Clone and configure:
   ```bash
   git clone https://github.com/n24q02m/better-telegram-mcp.git
   cd better-telegram-mcp
   cp .env.example .env
   # edit .env: set PUBLIC_URL=https://your-domain.com and MCP_DCR_SERVER_SECRET (random 32+ bytes)
   ```

2. Bundled Telegram dev credentials (`api_id=37984984`, `api_hash=2f5f4c76c4de7c07302380c788390100`) are baked into the image -- you do **not** need to register at my.telegram.org. Each user authenticates through the relay form by entering their own phone number and OTP code.

3. Start the server (Docker compose recommended):
   ```bash
   docker compose up -d
   ```
   The server binds `HOST=0.0.0.0` and serves multi-user mode by default with per-JWT-sub credential isolation.

4. Configure your MCP client to use your domain:
   ```json
   {
     "mcpServers": {
       "telegram": {
         "url": "https://your-domain.com/mcp"
       }
     }
   }
   ```

See `oci-vm-prod/services/better-telegram-mcp/docker-compose.yml` for a reference compose file.

### Edge auth: relay password

Public HTTP deployments expose `<your-domain>/authorize` to URL discovery. To prevent random Internet users from accessing the relay form, mint a relay password:

```bash
openssl rand -hex 32
# Save in your skret / .env as:
MCP_RELAY_PASSWORD=<generated-32-byte-hex>
```

Share this password out-of-band (Signal/email/SMS) with anyone you invite to use your server. They will see a login form when first opening `/authorize`; once logged in, the cookie persists 24 hours.

**Single-user dev exception**: If `PUBLIC_URL=http://localhost:8080`, you can leave `MCP_RELAY_PASSWORD` empty to disable the gate. The server logs a warning if you skip the password with a non-localhost `PUBLIC_URL`.

## Environment Variable Reference

### Stdio Mode (Bot Only)

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Yes | -- | Bot token from @BotFather |

### HTTP Mode (Bot + User)

HTTP mode credentials are entered via the browser-based relay form, not env vars. Server-side env vars for self-hosting:

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `PUBLIC_URL` | Self-host | -- | Public URL of the server (enables multi-user) |
| `MCP_DCR_SERVER_SECRET` | Self-host | -- | DCR server secret (32+ random bytes) |
| `HOST` | Self-host | `127.0.0.1` | Bind address (`0.0.0.0` for Docker) |
| `PORT` | Self-host | `8000` | HTTP port |

The bundled Telegram dev `api_id` (`37984984`) and `api_hash` (`2f5f4c76c4de7c07302380c788390100`) are public dev credentials baked into the source.

## Troubleshooting

### Bot cannot send messages

Bots can only message users who have started a conversation with the bot first. Have the target user send `/start` to your bot.

### Bot token does not work

Verify the token format: `<bot_id>:<token_secret>` (e.g., `123456789:ABCdefGHI-JKLmnoPQRstUVwxyz`). Re-issue from @BotFather if needed.

### Need to read messages or browse chat history

Bot mode (stdio Methods 1-2) cannot read messages or browse chats -- the Bot API does not expose these capabilities. Switch to HTTP mode (Method 3) and authenticate as a user via phone+OTP.

### OTP code not received (HTTP user mode)

The OTP code is sent to the **Telegram app** as a message from "Telegram" service notifications, not via SMS. Open your Telegram app on any device.

### Session expired (HTTP user mode)

Re-run the `/authorize` flow on the HTTP server -- the relay form will prompt for phone+OTP again.

### 2FA password prompt

2FA passwords are entered via the relay form during OTP authentication. They are never stored in environment variables or files.

### "FloodWaitError" from Telegram

Telegram rate-limits API calls. Wait the indicated time before retrying. The server handles this automatically for most operations.
