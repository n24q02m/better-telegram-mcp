"""Config schema for relay page setup."""

from mcp_relay_core.schema.types import RelayConfigSchema

RELAY_SCHEMA: RelayConfigSchema = {
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
