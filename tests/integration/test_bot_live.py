"""Integration tests for BotBackend against the live Telegram Bot API.

These tests require a valid TELEGRAM_BOT_TOKEN environment variable.
They only exercise operations that do NOT require a chat partner.
"""

from __future__ import annotations

import json
import os

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.bot_backend import BotBackend, TelegramAPIError
from better_telegram_mcp.tools.config_tool import handle_config
from better_telegram_mcp.tools.help_tool import handle_help

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set"),
]


# --- Fixtures ---


@pytest.fixture
async def bot():
    """Create a connected BotBackend for testing."""
    backend = BotBackend(BOT_TOKEN)
    await backend.connect()
    yield backend
    await backend.disconnect()


@pytest.fixture
def bot_id(bot: BotBackend) -> int:
    """Extract bot user ID from connected backend."""
    return bot._bot_info["id"]


# --- Connection ---


async def test_connect_success():
    """BotBackend.connect() succeeds with a valid token."""
    backend = BotBackend(BOT_TOKEN)
    await backend.connect()
    assert await backend.is_connected()
    await backend.disconnect()


async def test_connect_populates_bot_info():
    """connect() populates _bot_info with getMe data."""
    backend = BotBackend(BOT_TOKEN)
    await backend.connect()
    info = backend._bot_info
    assert info["is_bot"] is True
    assert isinstance(info["id"], int)
    assert isinstance(info["first_name"], str)
    assert len(info["first_name"]) > 0
    await backend.disconnect()


async def test_connect_bot_username():
    """The connected bot has the expected username."""
    backend = BotBackend(BOT_TOKEN)
    await backend.connect()
    assert backend._bot_info.get("username") == "better_telegram_mcp_bot"
    await backend.disconnect()


async def test_disconnect(bot: BotBackend):
    """disconnect() sets connected to False."""
    assert await bot.is_connected()
    await bot.disconnect()
    assert not await bot.is_connected()


async def test_connect_invalid_token():
    """connect() with an invalid token raises TelegramAPIError."""
    backend = BotBackend("0000000000:INVALID_TOKEN_FOR_TESTING")
    with pytest.raises(TelegramAPIError, match="Invalid bot token"):
        await backend.connect()


# --- getChat (bot's own chat) ---


async def test_get_chat_info_bot_self(bot: BotBackend, bot_id: int):
    """get_chat_info() works when querying the bot's own ID."""
    chat = await bot.get_chat_info(bot_id)
    assert chat["id"] == bot_id
    assert chat["type"] == "private"


async def test_get_chat_info_invalid_id(bot: BotBackend):
    """get_chat_info() with a non-existent chat raises TelegramAPIError."""
    with pytest.raises(TelegramAPIError):
        await bot.get_chat_info(999999999999)


# --- Mode restrictions (user-only operations) ---


async def test_search_messages_requires_user_mode(bot: BotBackend):
    """search_messages raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.search_messages("test")


async def test_list_chats_requires_user_mode(bot: BotBackend):
    """list_chats raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.list_chats()


async def test_create_chat_requires_user_mode(bot: BotBackend):
    """create_chat raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.create_chat("Test Group")


async def test_join_chat_requires_user_mode(bot: BotBackend):
    """join_chat raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.join_chat("https://t.me/+abc")


async def test_list_contacts_requires_user_mode(bot: BotBackend):
    """list_contacts raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.list_contacts()


async def test_search_contacts_requires_user_mode(bot: BotBackend):
    """search_contacts raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.search_contacts("John")


async def test_add_contact_requires_user_mode(bot: BotBackend):
    """add_contact raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.add_contact("+1234567890", "John")


async def test_block_user_requires_user_mode(bot: BotBackend):
    """block_user raises ModeError in bot mode."""
    with pytest.raises(ModeError, match="requires user mode"):
        await bot.block_user(123)


# --- Bot-mode limitations ---


async def test_get_history_returns_empty(bot: BotBackend, bot_id: int):
    """Bot API cannot read arbitrary chat history — returns empty list."""
    result = await bot.get_history(bot_id)
    assert result == []


async def test_download_media_not_implemented(bot: BotBackend):
    """download_media raises NotImplementedError in bot mode."""
    with pytest.raises(NotImplementedError, match="Bot API download requires"):
        await bot.download_media(123, 42)


async def test_clear_cache_noop(bot: BotBackend):
    """clear_cache is a no-op for bot mode (stateless)."""
    await bot.clear_cache()  # Should not raise


# --- Config tool ---


async def test_config_status_connected(bot: BotBackend):
    """config status action returns connected=True for a live bot."""
    result_str = await handle_config(bot, "status")
    result = json.loads(result_str)
    assert result["mode"] == "bot"
    assert result["connected"] is True
    assert "config" in result


async def test_config_set_and_read_back(bot: BotBackend):
    """config set action updates runtime config."""
    from better_telegram_mcp.server import _runtime_config

    original_limit = _runtime_config["message_limit"]
    try:
        result_str = await handle_config(bot, "set", message_limit=42)
        result = json.loads(result_str)
        assert result["updated"]["message_limit"] == 42
        assert result["current"]["message_limit"] == 42
    finally:
        _runtime_config["message_limit"] = original_limit


async def test_config_cache_clear(bot: BotBackend):
    """config cache_clear action succeeds."""
    result_str = await handle_config(bot, "cache_clear")
    result = json.loads(result_str)
    assert result["message"] == "Cache cleared."


async def test_config_unknown_action(bot: BotBackend):
    """config with unknown action returns error."""
    result_str = await handle_config(bot, "nonexistent")
    result = json.loads(result_str)
    assert "error" in result


# --- Help tool ---


def test_help_returns_documentation():
    """help tool returns non-empty documentation for 'all'."""
    result = handle_help("all")
    assert len(result) > 100
    assert "error" not in result.lower() or "ModeError" in result


def test_help_messages_topic():
    """help tool returns documentation for 'messages' topic."""
    result = handle_help("messages")
    assert len(result) > 50


def test_help_chats_topic():
    """help tool returns documentation for 'chats' topic."""
    result = handle_help("chats")
    assert len(result) > 50


def test_help_media_topic():
    """help tool returns documentation for 'media' topic."""
    result = handle_help("media")
    assert len(result) > 50


def test_help_contacts_topic():
    """help tool returns documentation for 'contacts' topic."""
    result = handle_help("contacts")
    assert len(result) > 50


def test_help_invalid_topic():
    """help tool returns error for invalid topic."""
    result = handle_help("nonexistent")
    result_data = json.loads(result)
    assert "error" in result_data


def test_help_none_returns_all():
    """help(None) returns all documentation."""
    result = handle_help(None)
    assert len(result) > 100


# --- Backend properties ---


async def test_bot_mode_is_bot(bot: BotBackend):
    """Backend mode is 'bot'."""
    assert bot.mode == "bot"


async def test_manage_topics_list_returns_error(bot: BotBackend):
    """manage_topics('list') returns error in bot mode (not supported)."""
    result = await bot.manage_topics(123, "list")
    assert "error" in result
    assert "Bot API does not support listing forum topics" in result["error"]
