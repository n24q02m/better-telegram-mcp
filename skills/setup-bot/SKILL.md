---
name: setup-bot
description: Diagnose and fix Telegram bot connection issues -- verify config, test send, resolve common errors
argument-hint: "[error message or symptom]"
---

# Setup Bot -- Error Diagnosis

Diagnose and fix Telegram bot connectivity issues. This skill assumes the bot already exists in BotFather -- focus is on getting it working with better-telegram-mcp.

## Steps

1. **Verify connection status**:
   - `config(action="status")` to check current bot token and connection state
   - If status shows "not configured", the user needs to set `TELEGRAM_BOT_TOKEN` env var and restart the MCP server (token is NOT runtime-configurable)

2. **Test send to obtain chat_id**:
   - `chats(action="list")` to see known chats
   - If no chats appear, instruct user to send any message to the bot first (the bot must receive at least one message to discover chat_id)
   - Send test: `messages(action="send", chat_id="<id>", text="Connection test")`

3. **Diagnose errors** using the flowchart below

## Error Diagnosis Flowchart

```
Send fails
  |
  +-- HTTP 403 "Forbidden: bot was blocked by the user"
  |     -> User blocked the bot. They must unblock it in Telegram.
  |
  +-- HTTP 403 "Forbidden: bot is not a member of the channel/group"
  |     -> Bot not added to the group/channel.
  |     -> For groups: add bot as member via group settings.
  |     -> For channels: add bot as admin (channels require admin for posting).
  |
  +-- HTTP 400 "Bad Request: chat not found"
  |     -> Wrong chat_id format.
  |     -> Groups use negative IDs (e.g., -1001234567890).
  |     -> Channels use negative IDs or @channel_username.
  |     -> Users use positive numeric IDs.
  |
  +-- HTTP 400 "Bad Request: can't parse entities"
  |     -> MarkdownV2 formatting error. See channel-post skill for escaping rules.
  |
  +-- HTTP 401 "Unauthorized"
  |     -> Bot token is invalid or revoked.
  |     -> Verify token with @BotFather (/mybots -> select bot -> API Token).
  |     -> If token was regenerated, update TELEGRAM_BOT_TOKEN and restart.
  |
  +-- HTTP 429 "Too Many Requests"
  |     -> Rate limited. Wait the retry_after seconds indicated in the response.
  |     -> Telegram limits: ~30 messages/second globally, 1 msg/second per chat.
  |
  +-- Connection timeout / DNS resolution failed
  |     -> Network issue. Check internet connectivity.
  |     -> If behind proxy/firewall, Telegram API (api.telegram.org) may be blocked.
  |
  +-- "Not Found" on getMe
        -> Token format is wrong. Must be "123456:ABC-DEF..." format.
```

## When to Use

- Bot token is set but messages fail to send
- Unclear error messages from Telegram API
- Bot works in DM but not in group/channel (or vice versa)
- Connection timeouts or auth failures after token rotation
