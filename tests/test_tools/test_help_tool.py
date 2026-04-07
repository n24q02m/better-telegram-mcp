from __future__ import annotations

import json

import pytest

from better_telegram_mcp.tools.help_tool import handle_help


@pytest.mark.asyncio
async def test_help_messages():
    result = await handle_help("messages")
    assert "Telegram Messages" in result
    assert "send" in result


@pytest.mark.asyncio
async def test_help_chats():
    result = await handle_help("chats")
    assert "Telegram Chats" in result
    assert "list" in result


@pytest.mark.asyncio
async def test_help_media():
    result = await handle_help("media")
    assert "Telegram Media" in result
    assert "send_photo" in result


@pytest.mark.asyncio
async def test_help_contacts():
    result = await handle_help("contacts")
    assert "Telegram Contacts" in result
    assert "block" in result


@pytest.mark.asyncio
async def test_help_all():
    result = await handle_help("all")
    assert "Telegram Messages" in result
    assert "Telegram Chats" in result
    assert "Telegram Media" in result
    assert "Telegram Contacts" in result


@pytest.mark.asyncio
async def test_help_none():
    result = await handle_help(None)
    assert "Telegram Messages" in result
    assert "Telegram Chats" in result


@pytest.mark.asyncio
async def test_help_telegram_topic():
    """Topic 'telegram' returns all docs (same as 'all')."""
    result = await handle_help("telegram")
    assert "Telegram Messages" in result
    assert "Telegram Chats" in result
    assert "Telegram Media" in result
    assert "Telegram Contacts" in result


@pytest.mark.asyncio
async def test_help_unknown_topic():
    result = await handle_help("nonexistent")
    parsed = json.loads(result)
    assert "error" in parsed
    assert "Unknown topic" in parsed["error"]


@pytest.mark.asyncio
async def test_help_missing_doc_file(monkeypatch):
    from pathlib import Path

    import better_telegram_mcp.tools.help_tool

    monkeypatch.setattr(
        better_telegram_mcp.tools.help_tool,
        "_DOCS_DIR",
        Path("/tmp/nonexistent_docs_dir_123"),
    )

    result = await handle_help("messages")
    parsed = json.loads(result)
    assert "error" in parsed
    assert "not found" in parsed["error"]


@pytest.mark.asyncio
async def test_help_all_no_docs(monkeypatch):
    from pathlib import Path

    import better_telegram_mcp.tools.help_tool

    monkeypatch.setattr(
        better_telegram_mcp.tools.help_tool,
        "_DOCS_DIR",
        Path("/tmp/nonexistent_docs_dir_123"),
    )

    result = await handle_help("all")
    parsed = json.loads(result)
    assert "error" in parsed


@pytest.mark.asyncio
async def test_help_caching(monkeypatch):
    from pathlib import Path
    from unittest.mock import MagicMock

    import better_telegram_mcp.tools.help_tool

    # Clear cache before test
    better_telegram_mcp.tools.help_tool._read_doc_sync.cache_clear()

    # Mock Path.exists and Path.read_text
    mock_read = MagicMock(return_value="Cached content")
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(Path, "read_text", mock_read)

    try:
        # First call
        result1 = await handle_help("messages")
        assert result1 == "Cached content"
        assert mock_read.call_count == 1

        # Second call (same topic)
        result2 = await handle_help("messages")
        assert result2 == "Cached content"
        # Should still be 1 because it's cached
        assert mock_read.call_count == 1

        # Third call (different topic)
        result3 = await handle_help("chats")
        assert result3 == "Cached content"
        assert mock_read.call_count == 2
    finally:
        # Clean up cache
        better_telegram_mcp.tools.help_tool._read_doc_sync.cache_clear()
