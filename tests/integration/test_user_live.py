"""Integration tests for UserBackend against the live Telegram MTProto API.

These tests require TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables,
plus an authorized session file at ~/.better-telegram-mcp/default.session.

They only exercise read-only operations — no sending, deleting, or destructive actions.
"""

from __future__ import annotations

import json
import os

import pytest

from better_telegram_mcp.backends.user_backend import UserBackend
from better_telegram_mcp.config import Settings
from better_telegram_mcp.tools.config_tool import handle_config
from better_telegram_mcp.tools.help_tool import handle_help

API_ID = os.environ.get("TELEGRAM_API_ID", "")
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not API_ID or not API_HASH, reason="User mode credentials not set"
    ),
]


# --- Fixtures ---


@pytest.fixture
def settings() -> Settings:
    """Build Settings from env vars for user mode."""
    return Settings()


@pytest.fixture
async def user(settings: Settings):
    """Create a connected and authorized UserBackend for testing."""
    backend = UserBackend(settings)
    await backend.connect()
    assert await backend.is_authorized(), "Session not authorized — run `auth` first"
    yield backend
    await backend.disconnect()


# --- Connection & Auth ---


async def test_connect_and_authorized(settings: Settings):
    """UserBackend.connect() succeeds and session is authorized."""
    backend = UserBackend(settings)
    await backend.connect()
    assert await backend.is_connected()
    assert await backend.is_authorized()
    await backend.disconnect()


async def test_disconnect(user: UserBackend):
    """disconnect() sets connected to False."""
    assert await user.is_connected()
    await user.disconnect()
    assert not await user.is_connected()


async def test_user_mode_is_user(user: UserBackend):
    """Backend mode is 'user'."""
    assert user.mode == "user"


# --- list_chats ---


async def test_list_chats_returns_dialogs(user: UserBackend):
    """list_chats() returns a non-empty list of dialogs."""
    chats = await user.list_chats(limit=10)
    assert isinstance(chats, list)
    assert len(chats) > 0
    # Each dialog has expected keys
    first = chats[0]
    assert "id" in first
    assert "title" in first
    assert "unread_count" in first


async def test_list_chats_respects_limit(user: UserBackend):
    """list_chats() respects the limit parameter."""
    chats = await user.list_chats(limit=3)
    assert len(chats) <= 3


# --- search_messages ---


async def test_search_messages_in_saved(user: UserBackend):
    """search_messages() in Saved Messages returns a list (may be empty)."""
    results = await user.search_messages("hello", chat_id="me", limit=5)
    assert isinstance(results, list)
    for msg in results:
        assert "message_id" in msg
        assert "text" in msg
        assert "date" in msg


async def test_search_messages_global(user: UserBackend):
    """search_messages() globally returns a list."""
    results = await user.search_messages("Telegram", limit=5)
    assert isinstance(results, list)
    for msg in results:
        assert "message_id" in msg


# --- get_history ---


async def test_get_history_saved_messages(user: UserBackend):
    """get_history('me') returns messages from Saved Messages."""
    messages = await user.get_history("me", limit=5)
    assert isinstance(messages, list)
    # Saved Messages may be empty for a fresh account, but should not error
    for msg in messages:
        assert "message_id" in msg
        assert "text" in msg
        assert "date" in msg


async def test_get_history_respects_limit(user: UserBackend):
    """get_history() respects the limit parameter."""
    messages = await user.get_history("me", limit=2)
    assert len(messages) <= 2


# --- get_chat_info ---


async def test_get_chat_info_self(user: UserBackend):
    """get_chat_info('me') returns info about the current user."""
    info = await user.get_chat_info("me")
    assert "id" in info
    assert isinstance(info["id"], int)
    # User entity should have first_name
    assert "first_name" in info


async def test_get_chat_info_returns_username(user: UserBackend):
    """get_chat_info('me') includes username for the authenticated user."""
    info = await user.get_chat_info("me")
    # The test account @n24q02m should have a username
    assert "username" in info


# --- list_contacts ---


async def test_list_contacts(user: UserBackend):
    """list_contacts() returns a list (may be empty)."""
    contacts = await user.list_contacts()
    assert isinstance(contacts, list)
    for contact in contacts:
        assert "id" in contact
        assert "first_name" in contact


# --- search_contacts ---


async def test_search_contacts(user: UserBackend):
    """search_contacts() returns a list of matching users."""
    results = await user.search_contacts("Telegram")
    assert isinstance(results, list)
    for user_info in results:
        assert "id" in user_info
        assert "first_name" in user_info


# --- clear_cache ---


async def test_clear_cache_no_error(user: UserBackend):
    """clear_cache() completes without error."""
    await user.clear_cache()


# --- Config tool ---


async def test_config_status_user_mode(user: UserBackend):
    """config status reports mode=user, connected=True, authorized=True."""
    result_str = await handle_config(user, "status")
    result = json.loads(result_str)
    assert result["mode"] == "user"
    assert result["connected"] is True
    assert result["authorized"] is True
    assert "config" in result


async def test_config_cache_clear(user: UserBackend):
    """config cache_clear action succeeds in user mode."""
    result_str = await handle_config(user, "cache_clear")
    result = json.loads(result_str)
    assert result["message"] == "Cache cleared."


async def test_config_unknown_action(user: UserBackend):
    """config with unknown action returns error in user mode."""
    result_str = await handle_config(user, "nonexistent")
    result = json.loads(result_str)
    assert "error" in result


# --- Help tool ---


@pytest.mark.asyncio
async def test_help_returns_documentation():
    """help tool returns non-empty documentation."""
    result = await handle_help("all")
    assert len(result) > 100


@pytest.mark.asyncio
async def test_help_messages_topic():
    """help tool returns documentation for messages topic."""
    result = await handle_help("messages")
    assert len(result) > 50


@pytest.mark.asyncio
async def test_help_contacts_topic():
    """help tool returns documentation for contacts topic."""
    result = await handle_help("contacts")
    assert len(result) > 50


@pytest.mark.asyncio
async def test_help_chats_topic():
    """help tool returns documentation for chats topic."""
    result = await handle_help("chats")
    assert len(result) > 50
