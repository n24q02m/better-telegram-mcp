"""Tests for relay_schema.py."""

from better_telegram_mcp.relay_schema import RELAY_SCHEMA


def test_relay_schema_structure():
    """Verify the RELAY_SCHEMA structure and content."""
    assert RELAY_SCHEMA["server"] == "better-telegram-mcp"
    assert RELAY_SCHEMA["displayName"] == "Telegram MCP"
    assert "modes" in RELAY_SCHEMA
    assert len(RELAY_SCHEMA["modes"]) == 2

    # Bot mode
    bot_mode = next(m for m in RELAY_SCHEMA["modes"] if m["id"] == "bot")
    assert bot_mode["label"] == "Bot Mode"
    assert bot_mode["description"] == "Use a Telegram Bot token"
    assert len(bot_mode["fields"]) == 1

    bot_field = bot_mode["fields"][0]
    assert bot_field["key"] == "TELEGRAM_BOT_TOKEN"
    assert bot_field["label"] == "Bot Token"
    assert bot_field["type"] == "password"
    assert "helpUrl" in bot_field
    assert "helpText" in bot_field

    # User mode
    user_mode = next(m for m in RELAY_SCHEMA["modes"] if m["id"] == "user")
    assert user_mode["label"] == "User Mode (MTProto)"
    assert user_mode["description"] == "Full account access"
    assert len(user_mode["fields"]) == 1

    user_field = user_mode["fields"][0]
    assert user_field["key"] == "TELEGRAM_PHONE"
    assert user_field["label"] == "Phone Number"
    assert user_field["type"] == "tel"
