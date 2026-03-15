# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please **DO NOT** create a public issue.

Instead, please email: **quangminh2402.dev@gmail.com**

Include:

1. Detailed description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

You will receive acknowledgment within 48 hours.

## Security Best Practices

When using better-telegram-mcp:

- **Never commit API keys** (bot tokens, API ID/hash) to version control
- Use environment variables or secure secret management
- Keep dependencies updated
- **Protect your session file** (`.session`) — it contains your Telegram authentication. The CLI sets `chmod 600` automatically, but verify permissions if you copy or move the file
- Store session files in a secure directory with restricted access
- Never share session files — they grant full access to your Telegram account
- Review message content before sending via the MCP server
