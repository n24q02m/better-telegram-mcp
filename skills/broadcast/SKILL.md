---
name: broadcast
description: Message broadcasting — select recipients, compose, preview, send with rate limiting
argument-hint: "[message or topic]"
---

# Broadcast Message

Send a message to multiple Telegram chats with rate limiting and preview.

## Steps

1. **Select recipients**:
   - `chats(action="list")` to see available chats
   - User selects target chats (groups, channels, or individual users)

2. **Compose message**:
   - Draft message content with the user
   - Choose parse mode: MarkdownV2 (recommended), HTML, or plain text
   - Add media if needed: `media(action="send_photo", ...)` or `media(action="send_document", ...)`

3. **Preview**:
   - Send to a test chat first: `messages(action="send", chat_id="<test_chat>", text="...", parse_mode="MarkdownV2")`
   - Confirm formatting looks correct

4. **Broadcast**:
   - Send to each recipient with appropriate delays (Telegram rate limit: ~30 messages/second)
   - Report delivery status for each recipient

5. **Summary**: Report successful/failed deliveries.

## When to Use

- Sending announcements to multiple groups/channels
- Notifying users about updates or events
- Distributing reports or summaries to stakeholders
