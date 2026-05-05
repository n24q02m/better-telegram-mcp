# Better Telegram MCP

mcp-name: io.github.n24q02m/better-telegram-mcp

**MCP server for Telegram with dual-mode support: Bot API (httpx) for quick bot integrations and MTProto (Telethon) for full user-account access.**

<!-- Badge Row 1: Status -->
[![CI](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/n24q02m/better-telegram-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/n24q02m/better-telegram-mcp/graph/badge.svg?token=d0fef60a-542e-4be2-9528-6e3a12931067)](https://codecov.io/gh/n24q02m/better-telegram-mcp)
[![PyPI](https://img.shields.io/pypi/v/better-telegram-mcp?logo=pypi&logoColor=white)](https://pypi.org/project/better-telegram-mcp/)
[![Docker](https://img.shields.io/docker/v/n24q02m/better-telegram-mcp?label=docker&logo=docker&logoColor=white&sort=semver)](https://hub.docker.com/r/n24q02m/better-telegram-mcp)
[![License: MIT](https://img.shields.io/github/license/n24q02m/better-telegram-mcp)](https://opensource.org/licenses/MIT)
[![SafeSkill 91/100](https://img.shields.io/badge/SafeSkill-91%2F100_Verified%20Safe-brightgreen)](https://safeskill.dev/scan/n24q02m-better-telegram-mcp)

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
- **6 tools** with action dispatch: `message`, `chat`, `media`, `contact`, `config`, `help`
- **Auto-detect mode** -- Set bot token for bot mode, or API credentials for user mode
- **Web-based OTP auth** -- Browser-based authentication with remote relay support for headless environments
- **Tool annotations** -- Each tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **MCP Resources** -- Documentation available as `telegram://docs/*` resources
- **Security hardened** -- SSRF protection, path traversal prevention, error sanitization

## Status

> **2026-05-02 -- Architecture stabilization update**
>
> Past months saw significant churn around credential handling and the daemon-bridge auto-spawn pattern. This caused multi-process races, browser tab spam, and inconsistent setup UX across plugins. **As of v&lt;auto&gt;, the architecture is stable**: 2 clean modes (stdio + HTTP), no daemon-bridge layer, no auto-spawn from stdio.
>
> Apologies for the instability period. If you encountered issues with prior versions, please update to v&lt;auto&gt;+ and follow the current [docs/setup-manual.md](docs/setup-manual.md) -- most prior workarounds are no longer needed.
>
> **Related plugins from the same author**:
> - [wet-mcp](https://github.com/n24q02m/wet-mcp) -- Web search + content extraction
> - [mnemo-mcp](https://github.com/n24q02m/mnemo-mcp) -- Persistent AI memory
> - [imagine-mcp](https://github.com/n24q02m/imagine-mcp) -- Image/video understanding + generation
> - [better-notion-mcp](https://github.com/n24q02m/better-notion-mcp) -- Notion API
> - [better-email-mcp](https://github.com/n24q02m/better-email-mcp) -- Email management
> - [better-telegram-mcp](https://github.com/n24q02m/better-telegram-mcp) -- Telegram
> - [better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) -- Godot Engine
> - [better-code-review-graph](https://github.com/n24q02m/better-code-review-graph) -- Code review knowledge graph
>
> All plugins share the same architecture -- install once, learn pattern transfers.

## Setup

- **Stdio mode** (default) -- `TELEGRAM_BOT_TOKEN` env var, bot mode only. See [setup-manual.md](docs/setup-manual.md).
- **HTTP mode** (encouraged) -- bot mode + user mode (MTProto via phone+OTP), browser-based setup with bundled api_id/hash. See [setup-manual.md](docs/setup-manual.md).

**With AI Agent** -- copy and send this to your AI agent:

> Please set up better-telegram-mcp for me. Follow this guide:
> https://raw.githubusercontent.com/n24q02m/better-telegram-mcp/main/docs/setup-with-agent.md

**Manual Setup** -- follow [docs/setup-manual.md](docs/setup-manual.md)

## Tools

| Tool | Actions | Description |
|:-----|:--------|:------------|
| `message` | `send`, `edit`, `delete`, `forward`, `pin`, `react`, `search`, `history` | Send, edit, delete, forward messages. Pin, react, search, browse history |
| `chat` | `list`, `info`, `create`, `join`, `leave`, `members`, `admin`, `settings`, `topics` | List and manage chats, groups, channels. Members, admin, forum topics |
| `media` | `send_photo`, `send_file`, `send_voice`, `send_video`, `download` | Send photos, files, voice notes, videos. Download media from messages |
| `contact` | `list`, `search`, `add`, `block` | List, search, add contacts. Block/unblock users (user mode only) |
| `config` | `status`, `set`, `cache_clear`, `setup_status`, `setup_start`, `setup_reset`, `setup_complete` | Server status, runtime settings, cache, credential setup (relay, status, reset, complete) |
| `help` | -- | Full documentation for any topic |

### MCP Resources

| URI | Content |
|:----|:--------|
| `telegram://docs/messages` | Message operations reference |
| `telegram://docs/chats` | Chat management reference |
| `telegram://docs/media` | Media send/download reference |
| `telegram://docs/contacts` | Contact management reference |
| `telegram://stats` | All documentation combined |

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

This plugin implements **TC-NearZK** (in-memory, ephemeral). See [mcp-core/docs/TRUST-MODEL.md](https://github.com/n24q02m/mcp-core/blob/main/docs/TRUST-MODEL.md) for full classification.

| Mode | Storage | Encryption | Who can read your data? |
|---|---|---|---|
| HTTP n24q02m-hosted (default) | In-memory `dict[sub] = MTProtoSession` | In-process only | Server process (cleared on restart) |
| HTTP self-host | Same as hosted | Same | Only you (admin = user) |
| stdio proxy | `~/.better-telegram-mcp/config.json` | AES-GCM, machine-bound key | Only your OS user (file perm 0600) |

## License

MIT -- See [LICENSE](LICENSE).
