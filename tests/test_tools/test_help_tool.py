from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

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

    import better_telegram_mcp.tools.help_tool

    # Clear cache before test
    better_telegram_mcp.tools.help_tool._read_doc_sync.cache_clear()

    # Mock the internal call to read_text by patching Path in the module
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = "Cached content"
    # Ensure __truediv__ returns the same mock path so _DOCS_DIR / file works
    mock_path.__truediv__.return_value = mock_path

    # Patch Path where it is used in help_tool
    monkeypatch.setattr(
        better_telegram_mcp.tools.help_tool, "Path", MagicMock(return_value=mock_path)
    )
    # Also need to patch the global _DOCS_DIR since it was already initialized
    monkeypatch.setattr(better_telegram_mcp.tools.help_tool, "_DOCS_DIR", mock_path)

    try:
        # First call
        result1 = await handle_help("messages")
        assert result1 == "Cached content"
        assert mock_path.read_text.call_count == 1

        # Second call (same topic)
        result2 = await handle_help("messages")
        assert result2 == "Cached content"
        # Should still be 1 because it's cached in _read_doc_sync
        assert mock_path.read_text.call_count == 1

        # Third call (different topic) - using a different mock for path if possible
        # or just realize that the lru_cache uses the path object as key.
        # Since we use the same mock_path object, it might still hit the cache if the path is same.
        # handle_help("chats") will use path = _DOCS_DIR / "chats.md"
        # our mock_path.__truediv__ returns mock_path.
        # So topic "chats" also results in mock_path.
        # Thus it hits the cache.

    finally:
        # Clean up cache
        better_telegram_mcp.tools.help_tool._read_doc_sync.cache_clear()
