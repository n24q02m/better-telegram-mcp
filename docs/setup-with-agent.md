# Better Telegram MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up better-telegram-mcp.

> **2026-05-02 Update (v&lt;auto&gt;+)**: Plugin install (Option 1) uses stdio mode with `TELEGRAM_BOT_TOKEN`. Bot mode only.
> User mode (MTProto via phone+OTP) is HTTP-only after this update.
> Set `TELEGRAM_BOT_TOKEN` in plugin config (Option 1), or switch to HTTP mode for user mode.

## Option 1: Claude Code Plugin (Recommended, stdio Bot Mode Only)

```bash
# Install from marketplace (includes skills: /setup-bot, /channel-post)
/plugin marketplace add n24q02m/claude-plugins
/plugin install better-telegram-mcp@n24q02m-plugins
```

Set `TELEGRAM_BOT_TOKEN` from [@BotFather](https://t.me/BotFather) in plugin settings or as a system env var. **Bot mode only** -- user mode (read messages, browse chats) requires HTTP (Option 4).

## Option 2: MCP Direct (stdio, Bot Mode Only)

**Python 3.13 required** -- Python 3.14+ is NOT supported.

### Claude Code (settings.json)

Add to `~/.claude/settings.local.json` under `"mcpServers"`:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uvx",
      "args": ["--python", "3.13", "better-telegram-mcp"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "123456789:ABCdef..."
      }
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
env = { TELEGRAM_BOT_TOKEN = "123456789:ABCdef..." }
```

### OpenCode (opencode.json)

Add to `opencode.json` in the project root:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uvx",
      "args": ["--python", "3.13", "better-telegram-mcp"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "123456789:ABCdef..."
      }
    }
  }
}
```

## Option 3: Docker (stdio, Bot Mode Only)

```bash
docker run -i --rm \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  n24q02m/better-telegram-mcp
```

Or as an MCP server config:

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

> Docker stdio supports bot mode only. For user mode, run the container in HTTP mode (Option 4 self-host).

## Why upgrade to HTTP mode?

Stdio (Options 1-3) is the simplest path for **bot mode**, but stdio cannot host the browser-based phone+OTP flow that **user mode** requires. Switch to HTTP for any of these reasons:

- **User mode access** (REQUIRED for user mode) -- read messages, browse chat history, list contacts, create groups/channels. Bot tokens cannot do this; only MTProto user sessions can. User mode auth is browser-based (phone + OTP code from Telegram app + optional 2FA password) and only HTTP transport hosts that flow.
- **claude.ai web compatibility** -- claude.ai supports HTTP MCP servers; stdio is desktop/CLI only.
- **One server, many sessions** -- a single HTTP server is shared across N Claude Code sessions instead of one stdio process per session.
- **Multi-device cred sync** -- log in once on any device; the server keeps the session.
- **Multi-user team sharing** -- HTTP supports per-JWT-sub credential isolation, so a team can share one self-hosted instance.
- **Always-on persistent process** -- enables webhook listeners, long-running agents, and scheduled tasks.

## Option 4: HTTP Remote (Multi-User, Bot + User Modes)

Use the live production endpoint (Dynamic Client Registration + relay form auth):

```json
{
  "mcpServers": {
    "telegram": {
      "url": "https://better-telegram-mcp.n24q02m.com/mcp"
    }
  }
}
```

The client registers a public DCR client at `/register`, then opens `/authorize` to fill the Telegram relay form. The form supports both modes:

- **Bot mode** -- paste your bot token from [@BotFather](https://t.me/BotFather)
- **User mode** -- enter your phone number, then the OTP code Telegram sends to your Telegram app, then your 2FA password if enabled

The server bundles public Telegram dev credentials (`api_id` and `api_hash`), so users do not need to register at [my.telegram.org](https://my.telegram.org). After the form completes, the server issues a Bearer JWT and tools become active immediately.

## Option 5: Self-Hosting HTTP Mode

For private deployments (single user or team), clone the repo and run via Docker:

```bash
git clone https://github.com/n24q02m/better-telegram-mcp.git
cd better-telegram-mcp
cp .env.example .env
# edit .env: PUBLIC_URL=https://your-domain.com, MCP_DCR_SERVER_SECRET=<32+ random bytes>
docker compose up -d
```

Bundled Telegram dev credentials (`api_id=37984984`, `api_hash=2f5f4c76c4de7c07302380c788390100`) are baked into the image -- no my.telegram.org registration needed. Each user authenticates through the relay form (phone + OTP).

Then point your MCP client at your domain:

```json
{
  "mcpServers": {
    "telegram": {
      "url": "https://your-domain.com/mcp"
    }
  }
}
```

## Environment Variables

### Stdio Mode (Bot Only)

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `TELEGRAM_BOT_TOKEN` | Yes | -- | Bot token from [@BotFather](https://t.me/BotFather) (format: `123456789:ABCdef...`) |

### HTTP Mode (Bot + User)

HTTP mode credentials are entered via the browser-based relay form, not env vars. Server-side env vars for self-hosting:

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `PUBLIC_URL` | Self-host | -- | Public URL of the server (enables multi-user) |
| `MCP_DCR_SERVER_SECRET` | Self-host | -- | DCR server secret (32+ random bytes) |
| `HOST` | Self-host | `127.0.0.1` | Bind address (`0.0.0.0` for Docker) |
| `PORT` | Self-host | `8000` | HTTP port |

The bundled Telegram dev `api_id` (`37984984`) and `api_hash` (`2f5f4c76c4de7c07302380c788390100`) are public dev credentials baked into the source.

## Mode Capabilities

| Feature | Bot (stdio or HTTP) | User (HTTP only) |
|:--------|:-------------------:|:----------------:|
| Send/Edit/Delete/Forward messages | Y | Y |
| Pin messages, React | Y | Y |
| Search messages, Browse history | -- | Y |
| List chats, Create groups/channels | -- | Y |
| Get chat info, Manage members | Y | Y |
| Send media (photo/file/voice/video) | Y | Y |
| Download media | -- | Y |
| Contacts (list/search/add/block) | -- | Y |

## Authentication

### Stdio Bot Mode

Set `TELEGRAM_BOT_TOKEN` env var. No web flow -- the server connects to the Bot API directly on startup.

### HTTP Bot Mode

Open the `/authorize` URL in any browser, choose **Bot Mode**, paste your bot token. Done.

### HTTP User Mode

Open the `/authorize` URL in any browser, choose **User Mode**:

1. Enter your phone number (with country code, e.g., `+84912345678`)
2. Click submit -- Telegram sends an OTP code to your **Telegram app** (not SMS)
3. Enter the OTP code on the same form
4. If 2FA is enabled, enter your 2FA password (never stored anywhere)
5. The server issues a Bearer JWT, tools become active immediately

Subsequent requests reuse the in-memory session keyed by your JWT subject (sub). Re-authenticate by repeating the `/authorize` flow.

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
