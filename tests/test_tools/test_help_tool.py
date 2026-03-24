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
async def test_help_unknown_topic():
    result = await handle_help("nonexistent")
    parsed = json.loads(result)
    assert "error" in parsed
    assert "Unknown topic" in parsed["error"]


@pytest.mark.asyncio
async def test_help_unknown_topic_with_suggestion():
    result = await handle_help("massage")
    parsed = json.loads(result)
    assert "error" in parsed
    assert "Unknown topic 'massage'." in parsed["error"]
    assert "Did you mean 'messages'?" in parsed["error"]


@pytest.mark.asyncio
async def test_help_missing_doc_file():
    from unittest.mock import AsyncMock, patch

    with patch(
        "better_telegram_mcp.tools.help_tool._load_doc",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await handle_help("messages")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"]


@pytest.mark.asyncio
async def test_help_all_no_docs():
    from unittest.mock import AsyncMock, patch

    with patch(
        "better_telegram_mcp.tools.help_tool._load_doc",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await handle_help("all")
        parsed = json.loads(result)
        assert "error" in parsed


@pytest.mark.asyncio
async def test_help_real_missing_docs(monkeypatch):
    import pathlib

    # Point _DOCS_DIR to an empty directory to test the `return None` path of `_load_doc`
    empty_dir = pathlib.Path("/tmp/nonexistent_docs_dir_for_testing")
    monkeypatch.setattr("better_telegram_mcp.tools.help_tool._DOCS_DIR", empty_dir)

    result_all = await handle_help("all")
    parsed_all = json.loads(result_all)
    assert "error" in parsed_all
    assert "No documentation found." in parsed_all["error"]

    result_single = await handle_help("messages")
    parsed_single = json.loads(result_single)
    assert "error" in parsed_single
    assert "Documentation for 'messages' not found." in parsed_single["error"]
