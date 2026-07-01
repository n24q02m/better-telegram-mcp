# Better Telegram MCP

mcp-name: io.github.n24q02m/better-telegram-mcp

**Telegram for AI agents -- messages, chats, media, and contacts across both bot and full user-account modes.**

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

<!-- BEGIN: AUTO-GENERATED-CROSS-PROMO -->
<details>
  <summary><strong>Sister projects from n24q02m</strong> (click to expand)</summary>

| Project | Tagline | Tag |
|---|---|---|
| [better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) | Knowledge graph for token-efficient code reviews -- semantic search and call-... | MCP |
| [better-email-mcp](https://github.com/n24q02m/better-email-mcp) | IMAP/SMTP email for AI agents -- read, send, organize folders, and manage att... | MCP |
| [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) | Composite MCP server for Godot Engine -- 17 composite tools for AI-assisted g... | MCP |
| [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) | Markdown-first Notion for AI agents -- pages, databases, blocks, and comments... | MCP |
| [better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) | Telegram for AI agents -- messages, chats, media, and contacts across both bo... | MCP |
| [claude-plugins](https://github.com/n24q02m/claude-plugins) | Claude Code plugin marketplace for the n24q02m MCP servers -- install web sea... | Marketplace |
| [imagine-mcp](https://github.com/n24q02m/imagine-mcp) | Image and video understanding + generation for AI agents -- across Gemini, Op... | MCP |
| [jules-task-archiver](https://github.com/n24q02m/jules-task-archiver) | Chrome Extension for bulk operations on Jules tasks via batchexecute API -- a... | Tooling |
| [mcp-core](https://github.com/n24q02m/mcp-core) | Shared foundation for building MCP servers -- Streamable HTTP transport, OAut... | MCP |
| [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) | Persistent AI memory with hybrid search and embedded sync. Open, free, unlimi... | MCP |
| [qwen3-embed](https://github.com/n24q02m/qwen3-embed) | Lightweight Qwen3 text embedding and reranking via ONNX Runtime and GGUF | Library |
| [skret](https://github.com/n24q02m/skret) | Secrets without the server. | CLI |
| [tacet](https://github.com/n24q02m/tacet) | TACET: a self-distilling neuro-symbolic cascade that amortises LLM cost in kn... | Tooling |
| [web-core](https://github.com/n24q02m/web-core) | Shared web infrastructure package for search, scraping, HTTP security, and st... | Library |
| [wet-mcp](https://github.com/n24q02m/wet-mcp) | Open-source MCP server for AI agents: web search, content extraction, and lib... | MCP |

</details>
<!-- END: AUTO-GENERATED-CROSS-PROMO -->

## Table of contents

- [Features](#features)
- [Status](#status)
- [Install](#install)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [Tools](#tools)
- [Comparison](#comparison)
- [Security](#security)
- [Build from Source](#build-from-source)
- [Trust Model](#trust-model)
- [License](#license)



<a href="https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/n24q02m/better-telegram-mcp/badge" alt="better-telegram-mcp MCP server" />
</a>

## Features

- **Dual mode** -- Bot API (httpx) for bots, MTProto (Telethon) for user accounts
- **7 tools** with action dispatch: `message`, `chat`, `media`, `contact`, `config`, `help`, `config__open_relay`
- **Auto-detect mode** -- Set bot token for bot mode, or API credentials for user mode
- **Web-based OTP auth** -- HTTP-mode browser relay form handles phone, OTP, and 2FA for user accounts (no session strings, no CLI sign-in)
- **Tool annotations** -- Each tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **MCP Resources** -- Documentation available as `telegram://docs/*` resources
- **Security hardened** -- SSRF protection, path traversal prevention, error sanitization

## Status

Two clean transports: **stdio** (default, bot mode) and **HTTP** (bot + user mode, browser relay setup, optional multi-user). No daemon-bridge layer and no auto-spawn from stdio. See [Modes overview](https://mcp.n24q02m.com/get-started/modes-overview/) for the full transport model.

Sister MCP servers from the same author are listed in the [collapsible section above](#better-telegram-mcp) -- they share this architecture, so install patterns transfer.

## Install

```bash
# Method 1 (default): plugin install via Claude Code (stdio, bot mode)
/plugin marketplace add n24q02m/claude-plugins
/plugin install better-telegram-mcp@n24q02m-plugins

# Method 1 (CLI): direct uvx invocation (stdio, bot mode)
claude mcp add telegram -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF -- uvx better-telegram-mcp

# Method 2 (fallback): Docker stdio
docker run -i --rm -e TELEGRAM_BOT_TOKEN=123456:ABC-DEF n24q02m/better-telegram-mcp

# Method 3 (recommended for user mode / multi-device / OAuth): Docker HTTP
docker run -d --name better-telegram-mcp-http -p 8080:8080 \
  -e MCP_TRANSPORT=http \
  -e PUBLIC_URL=https://telegram.example.com \
  -e MCP_DCR_SERVER_SECRET=<32+ random bytes> \
  n24q02m/better-telegram-mcp:latest
```

Stdio mode is **bot mode only** (`TELEGRAM_BOT_TOKEN`). User mode (full account via
phone + OTP) runs in HTTP mode, where credentials are entered through the
browser-based relay form at `/authorize`.

Full setup matrices live at the canonical docs site
[mcp.n24q02m.com/servers/better-telegram-mcp/setup/](https://mcp.n24q02m.com/servers/better-telegram-mcp/setup/),
and the paste-to-agent snippets at
[claude-plugins/plugins/better-telegram-mcp/setup-with-agent.md](https://github.com/n24q02m/claude-plugins/blob/main/plugins/better-telegram-mcp/setup-with-agent.md).

## Configuration

Settings load from `TELEGRAM_`-prefixed environment variables (Pydantic Settings).

**Stdio mode (bot only):**

| Variable | Required | Description |
|:---------|:---------|:------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from [@BotFather](https://t.me/BotFather) (format `123456789:ABCdef...`) |

**HTTP mode (bot + user):** credentials are entered via the browser relay form,
not env vars. Server-side env vars for self-hosting:

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `MCP_TRANSPORT` | Yes | `stdio` | Set to `http` to enable HTTP mode (`--http` CLI flag or `TRANSPORT_MODE=http` also work) |
| `PUBLIC_URL` | Self-host | -- | Public URL of the server; presence enables the multi-user OAuth branch |
| `MCP_DCR_SERVER_SECRET` | Self-host | -- | Multi-user OAuth shared secret, 32+ random bytes (legacy `DCR_SERVER_SECRET` still accepted) |
| `HOST` | No | `0.0.0.0` | Bind address |
| `PORT` | No | `8080` | HTTP port |

**User-mode credentials (optional overrides):** `TELEGRAM_API_ID` and
`TELEGRAM_API_HASH` ship with built-in public dev defaults, so only
`TELEGRAM_PHONE` is needed to start the phone + OTP flow. `TELEGRAM_SESSION_NAME`
and `TELEGRAM_DATA_DIR` customize the Telethon session file location. There is no
`TELEGRAM_PASSWORD` env var -- 2FA is entered through the web UI and never stored
in the environment.

## Documentation

Full docs at **[mcp.n24q02m.com/servers/better-telegram-mcp/setup/](https://mcp.n24q02m.com/servers/better-telegram-mcp/setup/)**:

- [Setup](https://mcp.n24q02m.com/servers/better-telegram-mcp/setup/) -- install methods for Claude Code, Codex, Gemini CLI, Cursor, Windsurf, mcp.json
- [Modes overview](https://mcp.n24q02m.com/get-started/modes-overview/) -- stdio (local, bot mode) and HTTP (remote, OAuth 2.1)
- [Multi-user setup](https://mcp.n24q02m.com/get-started/multi-user/) -- per-JWT-sub credential model

**Install with AI agent** -- paste this to your AI coding agent:

> Install MCP server `better-telegram-mcp` following the steps at
> https://raw.githubusercontent.com/n24q02m/claude-plugins/main/plugins/better-telegram-mcp/setup-with-agent.md

## Tools

| Tool | Actions | Description |
|:-----|:--------|:------------|
| `message` | `send`, `edit`, `delete`, `forward`, `pin`, `react`, `search`, `history` | Send, edit, delete, forward messages. Pin, react, search, browse history |
| `chat` | `list`, `info`, `create`, `join`, `leave`, `members`, `admin`, `settings`, `topics` | List and manage chats, groups, channels. Members, admin, forum topics |
| `media` | `send_photo`, `send_file`, `send_voice`, `send_video`, `download` | Send photos, files, voice notes, videos. Download media from messages |
| `contact` | `list`, `search`, `add`, `block` | List, search, add contacts. Block/unblock users (user mode only) |
| `config` | `status`, `set`, `cache_clear`, `setup_status`, `setup_start`, `setup_reset`, `setup_complete` | Server status, runtime settings, cache, credential setup (relay, status, reset, complete) |
| `help` | -- | Full documentation for any topic |
| `config__open_relay` | -- | Re-trigger the zero-config relay setup flow (prints a fresh relay URL for the browser form). Registered via `mcp-core`'s `register_open_relay_tool` so an LLM can restart setup without a manual restart |

### MCP Resources

| URI | Content |
|:----|:--------|
| `telegram://docs/messages` | Message operations reference |
| `telegram://docs/chats` | Chat management reference |
| `telegram://docs/media` | Media send/download reference |
| `telegram://docs/contacts` | Contact management reference |
| `telegram://stats` | All documentation combined |

## Comparison

How better-telegram-mcp stacks up against direct competitors in each pillar:

| Capability | better-telegram-mcp | chigwell/telegram-mcp | sparfenyuk/mcp-telegram | guangxiangdebizi/telegram-mcp |
|---|---|---|---|---|
| Bot API mode (bot token) | Yes (httpx) | No | No | Yes |
| MTProto user-account mode | Yes (Telethon) | Yes | Yes | No |
| Send / edit / delete messages | Yes | Yes | No (read-only, draft only) | Yes (send only) |
| Media download from messages | Yes | Yes | Yes | No (send only) |
| Contact management (add / block) | Yes (user mode) | Yes | Partial (list only) | No |
| Web-based / browser OTP auth | Yes (relay form, headless) | No (CLI session string) | No (CLI sign-in) | No (pre-set bot token) |
| Multi-user remote, per-user isolation | Yes (per-JWT-sub backends) | No | No | No |
| SSRF protection | Yes (URL validation + DNS-rebinding) | ? | ? | No |
| Path-traversal prevention | Yes | Yes (real-path allowed-root) | ? | No |
| Self-hostable | Yes | Yes | Yes | Yes |

## Security

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

## Trust Model

This plugin implements **TC-NearZK** (in-memory, ephemeral). See [mcp-core trust model](https://mcp.n24q02m.com/servers/mcp-core/trust-model/) for full classification.

| Mode | Storage | Encryption | Who can read your data? |
|---|---|---|---|
| HTTP n24q02m-hosted (default) | In-memory `dict[sub] = MTProtoSession` | In-process only | Server process (cleared on restart) |
| HTTP self-host | Same as hosted | Same | Only you (admin = user) |
| stdio | `~/.config/mcp/config.enc` (credentials) + `~/.better-telegram-mcp/<name>.session` (Telethon session) | AES-GCM, machine-bound key | Only your OS user (file perm 0600) |

## License

MIT -- See [LICENSE](LICENSE).
