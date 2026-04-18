from better_telegram_mcp.relay_schema import RELAY_SCHEMA, RELAY_SCHEMA_MODES


def test_relay_schema_structure():
    """Flat schema: server metadata + fields array covering both modes.

    Local OAuth form uses flat fields; the user fills ONE of:
      - TELEGRAM_BOT_TOKEN (bot mode)
      - TELEGRAM_PHONE (user mode)
    """
    assert RELAY_SCHEMA["server"] == "better-telegram-mcp"
    assert RELAY_SCHEMA["displayName"] == "Telegram MCP"
    field_keys = {f["key"] for f in RELAY_SCHEMA["fields"]}
    assert "TELEGRAM_BOT_TOKEN" in field_keys
    assert "TELEGRAM_PHONE" in field_keys


def test_relay_schema_modes_backward_compat():
    """Relay page uses modes for tabbed UI (bot + user)."""
    assert len(RELAY_SCHEMA_MODES["modes"]) == 2

    bot_mode = next(m for m in RELAY_SCHEMA_MODES["modes"] if m["id"] == "bot")
    assert bot_mode["label"] == "Bot Mode"
    assert any(f["key"] == "TELEGRAM_BOT_TOKEN" for f in bot_mode["fields"])

    user_mode = next(m for m in RELAY_SCHEMA_MODES["modes"] if m["id"] == "user")
    assert "User Mode" in user_mode["label"]
    assert any(f["key"] == "TELEGRAM_PHONE" for f in user_mode["fields"])
