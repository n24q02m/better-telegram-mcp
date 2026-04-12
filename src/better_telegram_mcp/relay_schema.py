"""Config schema for relay page setup.

Local OAuth form uses flat fields (bot token + phone).
User fills ONE of the two: bot token for bot mode, phone for user mode.
Relay page uses modes for tabbed UI — kept as RELAY_SCHEMA_MODES for backward compat.
"""

from typing import Any

RELAY_SCHEMA: dict[str, Any] = {
    "server": "better-telegram-mcp",
    "displayName": "Telegram MCP",
    "description": "Enter Bot Token for bot mode, OR Phone Number for user mode (MTProto).",
    "fields": [
        {
            "key": "TELEGRAM_BOT_TOKEN",
            "label": "Bot Token",
            "type": "password",
            "placeholder": "123456:ABC-DEF...",
            "helpUrl": "https://core.telegram.org/bots#botfather",
            "helpText": "Get from @BotFather on Telegram. Leave empty for user mode.",
            "required": False,
        },
        {
            "key": "TELEGRAM_PHONE",
            "label": "Phone Number (User Mode)",
            "type": "tel",
            "placeholder": "+84...",
            "helpText": "Full account access via MTProto. Leave empty for bot mode.",
            "required": False,
        },
    ],
    "capabilityInfo": [
        {
            "label": "Bot Mode",
            "priority": "Bot Token",
            "description": "Send/receive messages via Bot API. Limited to bot permissions.",
        },
        {
            "label": "User Mode",
            "priority": "Phone + OTP",
            "description": "Full account access via MTProto (Telethon). Requires phone verification.",
        },
    ],
}

RELAY_SCHEMA_MODES: dict[str, Any] = {
    "server": "better-telegram-mcp",
    "displayName": "Telegram MCP",
    "modes": [
        {
            "id": "bot",
            "label": "Bot Mode",
            "description": "Use a Telegram Bot token",
            "fields": [
                {
                    "key": "TELEGRAM_BOT_TOKEN",
                    "label": "Bot Token",
                    "type": "password",
                    "placeholder": "123456:ABC-DEF...",
                    "helpUrl": "https://core.telegram.org/bots#botfather",
                    "helpText": "Get from @BotFather on Telegram",
                }
            ],
        },
        {
            "id": "user",
            "label": "User Mode (MTProto)",
            "description": "Full account access",
            "fields": [
                {
                    "key": "TELEGRAM_PHONE",
                    "label": "Phone Number",
                    "type": "tel",
                    "placeholder": "+84...",
                },
            ],
        },
    ],
}
