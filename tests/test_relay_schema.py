from better_telegram_mcp.relay_schema import RELAY_SCHEMA


def test_relay_schema_structure():
    """Verify that the RELAY_SCHEMA is correctly defined."""
    assert RELAY_SCHEMA["server"] == "better-telegram-mcp"
    assert RELAY_SCHEMA["displayName"] == "Telegram MCP"
    assert "modes" in RELAY_SCHEMA
    assert len(RELAY_SCHEMA["modes"]) == 2


def test_bot_mode():
    """Verify that the bot mode is correctly defined."""
    bot_mode = next(
        (mode for mode in RELAY_SCHEMA["modes"] if mode["id"] == "bot"), None
    )
    assert bot_mode is not None
    assert bot_mode["label"] == "Bot Mode"
    assert bot_mode["description"] == "Use a Telegram Bot token"
    assert len(bot_mode["fields"]) == 1
    assert bot_mode["fields"][0]["key"] == "TELEGRAM_BOT_TOKEN"
    assert bot_mode["fields"][0]["type"] == "password"


def test_user_mode():
    """Verify that the user mode is correctly defined."""
    user_mode = next(
        (mode for mode in RELAY_SCHEMA["modes"] if mode["id"] == "user"), None
    )
    assert user_mode is not None
    assert user_mode["label"] == "User Mode (MTProto)"
    assert user_mode["description"] == "Full account access"
    assert len(user_mode["fields"]) == 1
    assert user_mode["fields"][0]["key"] == "TELEGRAM_PHONE"
    assert user_mode["fields"][0]["type"] == "tel"
