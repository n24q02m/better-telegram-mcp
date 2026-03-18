# Privacy Policy — Better Telegram MCP

**Last updated:** 2026-03-18

## Data Collection

Better Telegram MCP acts as a bridge between MCP clients (Claude, Cursor, etc.) and the Telegram API. It does **not** collect, store, or transmit any user data beyond what is necessary for the current operation.

## Auth Relay Server

When using the remote auth relay at `better-telegram-mcp.n24q02m.com`:

- **OTP codes** are relayed in-memory only and deleted immediately after use. No codes are logged or persisted.
- **Phone numbers** are masked (e.g., `+849***8069`) before being sent to the relay. The relay never receives or stores your full phone number.
- **2FA passwords** are relayed in-memory only and deleted immediately after use.
- **Sessions expire** after 10 minutes. The relay is stateless — no database, no disk storage.
- **Logging**: Only anonymous request metadata (timestamps, status codes) is logged. No message content, contacts, or credentials are logged.

## Local Mode (`TELEGRAM_AUTH_URL=local`)

When running with local auth:

- All data stays on your machine.
- The auth web server runs on `127.0.0.1` (localhost only) and shuts down after the MCP server stops.

## Session Files

- Telegram session files are stored locally at `~/.better-telegram-mcp/` with `600` permissions (owner-only).
- Session files contain your Telegram authentication. Treat them like passwords.
- Session files are never transmitted to any server.

## Telegram API Access

When authenticated, the MCP server can access your Telegram account with the same permissions as the official Telegram app. This includes reading/sending messages, managing contacts, and accessing chat history.

## Third-Party Services

- **Telegram API** (`api.telegram.org`, MTProto): Your data is subject to [Telegram's Privacy Policy](https://telegram.org/privacy).
- **Oracle Cloud**: The auth relay server runs on Oracle Cloud Infrastructure. See [Oracle Cloud Privacy](https://www.oracle.com/legal/privacy/services-privacy-policy.html).
- **Cloudflare**: DNS and tunnel proxy. See [Cloudflare Privacy](https://www.cloudflare.com/privacypolicy/).

## Contact

For privacy concerns, open an issue at [github.com/n24q02m/better-telegram-mcp/issues](https://github.com/n24q02m/better-telegram-mcp/issues).
