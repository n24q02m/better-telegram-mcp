from __future__ import annotations

import pytest

from better_telegram_mcp.server import mcp


def test_resources_registered():
    resources = mcp._resource_manager._resources
    expected_uris = {
        "telegram://docs/messages",
        "telegram://docs/chats",
        "telegram://docs/media",
        "telegram://docs/contacts",
        "telegram://stats",
    }
    assert {str(uri) for uri in resources.keys()} == expected_uris


@pytest.mark.asyncio
async def test_docs_messages_resource():
    resources = mcp._resource_manager._resources
    fn = resources["telegram://docs/messages"]
    result = await fn.fn()
    assert "Telegram Messages" in result


@pytest.mark.asyncio
async def test_docs_chats_resource():
    resources = mcp._resource_manager._resources
    fn = resources["telegram://docs/chats"]
    result = await fn.fn()
    assert "Telegram Chats" in result


@pytest.mark.asyncio
async def test_docs_media_resource():
    resources = mcp._resource_manager._resources
    fn = resources["telegram://docs/media"]
    result = await fn.fn()
    assert "Telegram Media" in result


@pytest.mark.asyncio
async def test_docs_contacts_resource():
    resources = mcp._resource_manager._resources
    fn = resources["telegram://docs/contacts"]
    result = await fn.fn()
    assert "Telegram Contacts" in result


@pytest.mark.asyncio
async def test_stats_resource():
    resources = mcp._resource_manager._resources
    fn = resources["telegram://stats"]
    result = await fn.fn()
    assert "Telegram Messages" in result
    assert "Telegram Chats" in result
