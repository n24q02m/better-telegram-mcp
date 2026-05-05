# Better Telegram MCP -- Agent Setup Guide

> Give this file to your AI agent to automatically set up better-telegram-mcp.

> **2026-05-02 Update (v&lt;auto&gt;+)**: Plugin install (Option 1) uses stdio mode with `TELEGRAM_BOT_TOKEN`. Bot mode only.
> User mode (MTProto via phone+OTP) is HTTP-only after this update.
> Set `TELEGRAM_BOT_TOKEN` in plugin config (Option 1), or switch to HTTP mode for user mode.

## Method overview

This plugin supports 3 install methods. Pick the one that matches your use case:

| Priority | Method | Transport | Best for |
|---|---|---|---|
| **1. Default** | Plugin install (`uvx`/`npx`) | stdio | Quick local start, single workstation, no OAuth/HTTP needed. |
| **2. Fallback** | Docker stdio (`docker run -i --rm`) | stdio | Windows/macOS where native uvx/npx hits PATH or Python version issues. |
| **3. Recommended** | Docker HTTP (`docker run -p 8080:8080`) | HTTP | Multi-device, OAuth/relay-form auth, team self-host, claude.ai web compatibility. |

All MCP servers across this stack share this priority hierarchy. Note: 2 plugins (`better-godot-mcp` and `better-code-review-graph`) only support Method 1 (stdio) -- they need direct host access to project files / repo paths and don't ship Docker / HTTP variants.

> **⚠️ Mutually exclusive — pick ONE per plugin**: If you choose Method 2 (Docker stdio override) OR Method 3 (HTTP), do NOT also `/plugin install` this plugin via marketplace. Both load simultaneously and create duplicate entries in `/mcp` dialog (plugin's stdio + your override). Plugin matching is by **endpoint** (URL or command string) per CC docs, not by name — and `npx`/`uvx` ≠ `docker` ≠ HTTP URL, so all three are distinct endpoints. Trade-off: choosing Method 2 or Method 3 means you lose this plugin's skills/agents/hooks/commands. For full plugin features, use Method 1 (default plugin install) with `userConfig` credentials prompted at install time.

## Option 1: Claude Code Plugin (Recommended, stdio Bot Mode Only)

### Credential prompts at install

When you run `/plugin install`, Claude Code prompts you for the following credentials (declared in `userConfig` per CC docs). Sensitive values are stored in your system keychain and persist across `/plugin update`:

| Field | Required | Where to obtain |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Optional (required for stdio bot mode) | From @BotFather. Note: HTTP user-mode (phone+OTP) is configured via relay form at `/authorize`, not via plugin install prompt. |

### Steps

```bash
# Install from marketplace (includes skills: /setup-bot, /channel-post)
/plugin marketplace add n24q02m/claude-plugins
/plugin install better-telegram-mcp@n24q02m-plugins
```

Paste your bot token when prompted. **Bot mode only** -- user mode (read messages, browse chats) requires HTTP (Option 3) and uses a separate auth flow (phone+OTP via web form, not `userConfig`).

> **Note**: This installs the full plugin (skills + agents + hooks + commands + stdio MCP server). If you'd rather use Option 2 (Docker stdio) or Option 3 (HTTP) below, DO NOT `/plugin install` this plugin — pick Option 2 or Option 3 instead. All three methods are mutually exclusive (see Method overview).

## Option 2: Docker stdio (fallback)

> **⚠️ Before adding the Docker stdio override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-telegram-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's `npx`/`uvx` stdio + your `docker run` stdio) will load simultaneously since plugin matches by endpoint (command string), not by name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. Use Option 1 instead if you want full plugin features.

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

> Docker stdio supports bot mode only. For user mode, run the container in HTTP mode (Option 3 self-host).

## Why upgrade to HTTP mode?

Stdio (Options 1-2) is the simplest path for **bot mode**, but stdio cannot host the browser-based phone+OTP flow that **user mode** requires. Switch to HTTP for any of these reasons:

- **User mode access** (REQUIRED for user mode) -- read messages, browse chat history, list contacts, create groups/channels. Bot tokens cannot do this; only MTProto user sessions can. User mode auth is browser-based (phone + OTP code from Telegram app + optional 2FA password) and only HTTP transport hosts that flow.
- **claude.ai web compatibility** -- claude.ai supports HTTP MCP servers; stdio is desktop/CLI only.
- **One server, many sessions** -- a single HTTP server is shared across N Claude Code sessions instead of one stdio process per session.
- **Multi-device cred sync** -- log in once on any device; the server keeps the session.
- **Multi-user team sharing** -- HTTP supports per-JWT-sub credential isolation, so a team can share one self-hosted instance.
- **Always-on persistent process** -- enables webhook listeners, long-running agents, and scheduled tasks.

## Option 3: Docker HTTP (recommended)

> **⚠️ Before adding the HTTP override below, ensure this plugin is NOT installed via marketplace**: Run `/plugin uninstall better-telegram-mcp@n24q02m-plugins` first if you previously ran `/plugin install`. Otherwise both entries (plugin's stdio + your HTTP override) will load simultaneously since plugin matches by endpoint, not name.
>
> **Trade-off accepted**: Choosing this method means you lose this plugin's skills/agents/hooks/commands. For example, the `better-telegram-mcp:setup-bot` skill will no longer be available. Use Option 1 instead if you want full plugin features.

> **Switching transport vs. setting credentials**: The `userConfig` prompt only configures credentials for stdio mode (Method 1 / Option 1). To switch transport to HTTP, override `mcpServers` in your client settings per the snippets below -- this is a separate path from `userConfig` and is not driven by the install prompt.

### 3.1. Hosted (n24q02m.com)

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

### 3.2. Self-host with docker-compose

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

### Edge auth: relay password

Public HTTP deployments expose `<your-domain>/authorize` to URL discovery. To prevent random Internet users from accessing the relay form, mint a relay password:

```bash
openssl rand -hex 32
# Save in your skret / .env as:
MCP_RELAY_PASSWORD=<generated-32-byte-hex>
```

Share this password out-of-band (Signal/email/SMS) with anyone you invite to use your server. They will see a login form when first opening `/authorize`; once logged in, the cookie persists 24 hours.

**Single-user dev exception**: If `PUBLIC_URL=http://localhost:8080`, you can leave `MCP_RELAY_PASSWORD` empty to disable the gate. The server logs a warning if you skip the password with a non-localhost `PUBLIC_URL`.

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
