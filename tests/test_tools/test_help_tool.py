from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from better_telegram_mcp.tools.help_tool import _read_doc_sync, handle_help


@pytest.fixture(autouse=True)
def clear_help_cache():
    """Clear the LRU cache for help tool to prevent cross-test leakage."""
    _read_doc_sync.cache_clear()


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
async def test_help_docs_are_cached(monkeypatch):
    """Test that reading the same doc multiple times only triggers one disk read."""
    from pathlib import Path

    import better_telegram_mcp.tools.help_tool

    # Create mock path that says it exists
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = "Mocked content"

    # We need to ensure that f"{topic}.md" on the mocked _DOCS_DIR returns our mock_path
    mock_docs_dir = MagicMock(spec=Path)
    mock_docs_dir.__truediv__.return_value = mock_path

    monkeypatch.setattr(better_telegram_mcp.tools.help_tool, "_DOCS_DIR", mock_docs_dir)

    # First read (should read from disk)
    result1 = await handle_help("messages")
    assert "Mocked content" in result1

    # Second read (should hit cache)
    result2 = await handle_help("messages")
    assert "Mocked content" in result2

    # Third read (should hit cache)
    result3 = await handle_help("messages")
    assert "Mocked content" in result3

    # read_text should only be called once
    assert mock_path.read_text.call_count == 1
    assert mock_path.exists.call_count == 1
