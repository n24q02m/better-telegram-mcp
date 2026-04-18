from better_telegram_mcp.relay_schema import RELAY_SCHEMA


def test_relay_schema_structure():
    assert RELAY_SCHEMA["server"] == "better-telegram-mcp"
    assert RELAY_SCHEMA["displayName"] == "Telegram MCP"
    assert len(RELAY_SCHEMA["modes"]) == 2

    # Check Bot Mode
    bot_mode = next(m for m in RELAY_SCHEMA["modes"] if m["id"] == "bot")
    assert bot_mode["label"] == "Bot Mode"
    assert any(f["key"] == "TELEGRAM_BOT_TOKEN" for f in bot_mode["fields"])

    # Check User Mode
    user_mode = next(m for m in RELAY_SCHEMA["modes"] if m["id"] == "user")
    assert user_mode["label"] == "User Mode (MTProto)"
    assert any(f["key"] == "TELEGRAM_PHONE" for f in user_mode["fields"])
