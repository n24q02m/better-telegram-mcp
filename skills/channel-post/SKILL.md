---
name: channel-post
description: Compose and post formatted content to a Telegram channel -- MarkdownV2 escaping, message splitting, media ordering
argument-hint: "[content to post]"
---

# Channel Post

Compose and post formatted content to a Telegram channel with correct formatting.

## Steps

1. **Identify target channel**:
   - `chats(action="list")` to find the channel
   - Channel chat_id is a negative number (e.g., -1001234567890) or @username

2. **Compose content** with the user:
   - Draft the message text
   - Apply MarkdownV2 formatting (see escaping rules below)
   - Determine if media attachments are needed

3. **Handle media attachments** (if any):
   - Photo with caption: `media(action="send_photo", chat_id="...", file_path="...", caption="...")` -- caption goes WITH the photo, not as a separate message
   - Document: `media(action="send_document", chat_id="...", file_path="...")`
   - Multiple photos: send as media group, first photo carries the caption

4. **Split long messages** if content exceeds 4096 characters:
   - Split at paragraph boundaries (double newline) to preserve readability
   - Each chunk must be independently valid MarkdownV2 (no unclosed formatting)
   - Send chunks sequentially with the same parse_mode

5. **Send and verify**:
   - `messages(action="send", chat_id="<channel>", text="<content>", parse_mode="MarkdownV2")`
   - Verify the message appears correctly in the channel
   - If formatting breaks, check the escaping rules below

## MarkdownV2 Escaping Rules

All these characters MUST be escaped with `\` when used as literal text (outside formatting markup):

```
_ * [ ] ( ) ~ ` > # + - = | { } . !
```

### Common patterns

| Intent | Correct MarkdownV2 |
|---|---|
| Bold text | `*bold*` |
| Italic text | `_italic_` |
| Code inline | `` `code` `` |
| Code block | ```` ```language\ncode\n``` ```` |
| Link | `[text](https://url)` |
| Literal dot in "v2.0" | `v2\.0` |
| Literal dash in list | `\- item` |
| Price "$9.99" | `\$9\.99` |
| Exclamation "Done!" | `Done\!` |
| Parenthetical "(note)" | `\(note\)` |
| Hashtag "#topic" | `\#topic` |

### Formatting inside formatting

When nesting, the inner delimiter must also be escaped:
- Bold italic: `*_bold italic_*` -- the `_` inside `*...*` does NOT need escaping
- But literal `_` inside bold: `*score\_value*` -- MUST escape

### Frequent mistakes

- Forgetting to escape `.` in URLs used as plain text (not inside `[](...)`)
- Forgetting to escape `!` at end of sentences
- Forgetting to escape `-` in bulleted lists (use `\-` or switch to HTML `<li>`)
- Unescaped `(` `)` in regular text (Telegram interprets them as link syntax)

## When to Use

- Publishing announcements, updates, or newsletters to a Telegram channel
- Posting formatted content (code snippets, tables, lists) to channels
- Sending content with images or documents to channels
- Any message that needs careful MarkdownV2 formatting
