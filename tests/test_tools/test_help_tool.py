from __future__ import annotations

import json

from better_telegram_mcp.tools.help_tool import handle_help


def test_help_messages():
    result = handle_help("messages")
    assert "Telegram Messages" in result
    assert "send" in result


def test_help_chats():
    result = handle_help("chats")
    assert "Telegram Chats" in result
    assert "list" in result


def test_help_media():
    result = handle_help("media")
    assert "Telegram Media" in result
    assert "send_photo" in result


def test_help_contacts():
    result = handle_help("contacts")
    assert "Telegram Contacts" in result
    assert "block" in result


def test_help_all():
    result = handle_help("all")
    assert "Telegram Messages" in result
    assert "Telegram Chats" in result
    assert "Telegram Media" in result
    assert "Telegram Contacts" in result


def test_help_none():
    result = handle_help(None)
    assert "Telegram Messages" in result
    assert "Telegram Chats" in result


def test_help_unknown_topic():
    result = handle_help("nonexistent")
    parsed = json.loads(result)
    assert "error" in parsed
    assert "Unknown topic" in parsed["error"]


def test_help_missing_doc_file():
    from unittest.mock import patch

    with patch("better_telegram_mcp.tools.help_tool._load_doc", return_value=None):
        result = handle_help("messages")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"]


def test_help_all_no_docs():
    from unittest.mock import patch

    with patch("better_telegram_mcp.tools.help_tool._load_doc", return_value=None):
        result = handle_help("all")
        parsed = json.loads(result)
        assert "error" in parsed
