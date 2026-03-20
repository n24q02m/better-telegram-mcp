---
name: setup-bot
description: Guided Telegram bot creation — create via BotFather, configure, test messaging
argument-hint: "[bot name]"
---

# Setup Telegram Bot

Guide the user through creating and configuring a Telegram bot.

## Steps

1. **Create bot via BotFather**:
   - Instruct user to message @BotFather on Telegram
   - Send `/newbot`, choose name and username
   - Copy the bot token

2. **Configure better-telegram-mcp**:
   - `config(action="set", key="TELEGRAM_BOT_TOKEN", value="<token>")`
   - Verify connection: `config(action="status")`

3. **Test messaging**:
   - Find chat ID: `chats(action="list")` or ask user to send a message to bot
   - Send test message: `messages(action="send", chat_id="<id>", text="Hello from bot!")`
   - Verify delivery

4. **Configure optional features**:
   - Webhook setup if needed
   - Parse mode preferences (MarkdownV2 recommended)

## When to Use

- First time setting up a Telegram bot with better-telegram-mcp
- Migrating from another bot framework
- Troubleshooting bot connectivity issues
