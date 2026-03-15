# Style Guide - better-telegram-mcp

## Architecture
Telegram MCP server with dual-mode support. Python, single-package repo.

## Python
- Formatter/Linter: Ruff (default config)
- Type checker: ty
- Test: pytest + pytest-asyncio
- Package manager: uv
- SDK: mcp[cli]
- Core deps: httpx (Bot API), Telethon (MTProto)

## Code Patterns
- Async/await with httpx.AsyncClient for Bot API operations
- Telethon client for MTProto user-mode operations
- Mega-tool pattern: 6 composite tools with action dispatch
- Auto-detect mode: API credentials -> user mode, bot token -> bot mode
- Session file management for persistent MTProto auth

## Commits
Conventional Commits (feat:, fix:, chore:, docs:, refactor:, test:).

## Security
Session files with 600 permissions. Validate all user inputs. No credential logging. Secure OTP handling.
