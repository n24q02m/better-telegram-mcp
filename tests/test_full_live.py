"""Full/real live MCP protocol tests for better-telegram-mcp (bot mode).

Spawns the MCP server as a subprocess and communicates via the MCP protocol
(JSON-RPC over stdio). All tests exercise tools through the actual transport
layer, NOT direct backend calls.

Requirements:
- TELEGRAM_BOT_TOKEN: valid bot token (hardcoded fallback for CI)
- TELEGRAM_TEST_CHAT_ID: chat ID where the bot can send messages
  (a user must have started a conversation with the bot first)

Run:
    TELEGRAM_BOT_TOKEN="..." TELEGRAM_TEST_CHAT_ID="..." \
        uv run pytest tests/test_full_live.py -m full -v --tb=short
"""

from __future__ import annotations

import json
import os
import struct
import tempfile
import zlib

import httpx
import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TEST_CHAT_ID = os.environ.get("TELEGRAM_TEST_CHAT_ID", "")

full = pytest.mark.full


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(result) -> dict | str:
    """Extract text from MCP call_tool result and parse as JSON if possible."""
    text = result.content[0].text
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def _server_params(*, with_token: bool = True) -> StdioServerParameters:
    """Build StdioServerParameters, optionally injecting BOT_TOKEN."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
    if with_token and BOT_TOKEN:
        env["TELEGRAM_BOT_TOKEN"] = BOT_TOKEN
    return StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "better_telegram_mcp"],
        env=env,
    )


async def _get_bot_id() -> int:
    """Get the bot's own user ID via the Telegram API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
        data = resp.json()
        return data["result"]["id"]


async def _discover_chat_id() -> int | None:
    """Try to discover a chat_id from recent updates."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"limit": 10},
        )
        data = resp.json()
        for update in data.get("result", []):
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            if chat.get("type") == "private" and chat.get("id"):
                return chat["id"]
    return None


async def _resolve_chat_id() -> int:
    """Resolve a chat_id for message-sending tests.

    Priority: TELEGRAM_TEST_CHAT_ID env > auto-discovery via getUpdates.
    """
    if TEST_CHAT_ID:
        return int(TEST_CHAT_ID)
    discovered = await _discover_chat_id()
    if discovered:
        return discovered
    pytest.skip(
        "No TELEGRAM_TEST_CHAT_ID set and no chats discovered via getUpdates. "
        "Send /start to the bot first, then set TELEGRAM_TEST_CHAT_ID."
    )


def _make_1x1_png() -> bytes:
    """Create a minimal valid 1x1 red PNG in memory."""
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return (
            struct.pack(">I", len(data))
            + c
            + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = zlib.compress(b"\x00\xff\x00\x00")
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", raw) + _chunk(b"IEND", b"")


# ---------------------------------------------------------------------------
# TestFullBotMessages
# ---------------------------------------------------------------------------


@full
@pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set")
class TestFullBotMessages:
    """Message operations via MCP protocol (requires a chat partner)."""

    @pytest.mark.timeout(30)
    async def test_send_and_delete(self):
        """Send a message and delete it."""
        chat_id = await _resolve_chat_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                msg_id = None
                try:
                    result = await session.call_tool(
                        "telegram",
                        {
                            "action": "send",
                            "chat_id": chat_id,
                            "text": "[test] send_and_delete",
                        },
                    )
                    data = _parse(result)
                    assert isinstance(data, dict), f"Expected dict, got {data}"
                    assert "error" not in data, f"Send failed: {data}"
                    msg_id = data.get("message_id")
                    assert msg_id is not None, f"No message_id: {data}"
                finally:
                    if msg_id:
                        await session.call_tool(
                            "telegram",
                            {
                                "action": "delete",
                                "chat_id": chat_id,
                                "message_id": msg_id,
                            },
                        )

    @pytest.mark.timeout(30)
    async def test_send_edit_delete(self):
        """Send a message, edit it, then delete."""
        chat_id = await _resolve_chat_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                msg_id = None
                try:
                    result = await session.call_tool(
                        "telegram",
                        {
                            "action": "send",
                            "chat_id": chat_id,
                            "text": "[test] before edit",
                        },
                    )
                    data = _parse(result)
                    assert "error" not in data, f"Send failed: {data}"
                    msg_id = data["message_id"]

                    result = await session.call_tool(
                        "telegram",
                        {
                            "action": "edit",
                            "chat_id": chat_id,
                            "message_id": msg_id,
                            "text": "[test] after edit",
                        },
                    )
                    data = _parse(result)
                    assert isinstance(data, dict)
                    assert "error" not in data, f"Edit failed: {data}"
                    assert data.get("text") == "[test] after edit"
                finally:
                    if msg_id:
                        await session.call_tool(
                            "telegram",
                            {
                                "action": "delete",
                                "chat_id": chat_id,
                                "message_id": msg_id,
                            },
                        )

    @pytest.mark.timeout(30)
    async def test_send_forward_delete(self):
        """Send a message, forward it to the same chat, delete both."""
        chat_id = await _resolve_chat_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                msg_id = None
                fwd_id = None
                try:
                    result = await session.call_tool(
                        "telegram",
                        {
                            "action": "send",
                            "chat_id": chat_id,
                            "text": "[test] forward me",
                        },
                    )
                    data = _parse(result)
                    assert "error" not in data, f"Send failed: {data}"
                    msg_id = data["message_id"]

                    result = await session.call_tool(
                        "telegram",
                        {
                            "action": "forward",
                            "from_chat": chat_id,
                            "to_chat": chat_id,
                            "message_id": msg_id,
                        },
                    )
                    data = _parse(result)
                    assert isinstance(data, dict)
                    assert "error" not in data, f"Forward failed: {data}"
                    fwd_id = data.get("message_id")
                finally:
                    for mid in (msg_id, fwd_id):
                        if mid:
                            await session.call_tool(
                                "telegram",
                                {
                                    "action": "delete",
                                    "chat_id": chat_id,
                                    "message_id": mid,
                                },
                            )

    @pytest.mark.timeout(30)
    async def test_send_pin_delete(self):
        """Send a message, pin it, then delete."""
        chat_id = await _resolve_chat_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                msg_id = None
                try:
                    result = await session.call_tool(
                        "telegram",
                        {
                            "action": "send",
                            "chat_id": chat_id,
                            "text": "[test] pin me",
                        },
                    )
                    data = _parse(result)
                    assert "error" not in data, f"Send failed: {data}"
                    msg_id = data["message_id"]

                    # Pin -- may fail in private chats, acceptable
                    result = await session.call_tool(
                        "telegram",
                        {
                            "action": "pin",
                            "chat_id": chat_id,
                            "message_id": msg_id,
                        },
                    )
                    data = _parse(result)
                    assert isinstance(data, dict)
                finally:
                    if msg_id:
                        await session.call_tool(
                            "telegram",
                            {
                                "action": "delete",
                                "chat_id": chat_id,
                                "message_id": msg_id,
                            },
                        )

    @pytest.mark.timeout(30)
    async def test_history_returns_result(self):
        """history action returns a result (may be empty in bot mode)."""
        chat_id = await _resolve_chat_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "history", "chat_id": chat_id, "limit": 5},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                if "messages" in data:
                    assert isinstance(data["messages"], list)

    @pytest.mark.timeout(30)
    async def test_search_mode_error(self):
        """search action returns mode error in bot mode (user-only)."""
        chat_id = await _resolve_chat_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {
                        "action": "search",
                        "query": "test",
                        "chat_id": chat_id,
                    },
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" in data


# ---------------------------------------------------------------------------
# TestFullBotChats
# ---------------------------------------------------------------------------


@full
@pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set")
class TestFullBotChats:
    """Chat operations via MCP protocol."""

    @pytest.mark.timeout(30)
    async def test_chats_info_bot_self(self):
        """chats info on the bot's own ID returns chat data."""
        bot_id = await _get_bot_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "chat_info", "chat_id": bot_id},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" not in data, f"Info failed: {data}"
                assert data.get("id") == bot_id
                assert data.get("type") == "private"

    @pytest.mark.timeout(30)
    async def test_chats_members_private_error(self):
        """chats members on a private chat returns error (no admins)."""
        bot_id = await _get_bot_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "chat_members", "chat_id": bot_id},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                # Private chats have no admins -- expect error or empty result
                if "error" in data:
                    assert isinstance(data["error"], str)
                elif "members" in data:
                    assert isinstance(data["members"], list)

    @pytest.mark.timeout(30)
    async def test_chats_list_mode_error(self):
        """chats list in bot mode returns mode error."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "list_chats"},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" in data


# ---------------------------------------------------------------------------
# TestFullBotMedia
# ---------------------------------------------------------------------------


@full
@pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set")
class TestFullBotMedia:
    """Media operations via MCP protocol (requires a chat partner)."""

    @pytest.mark.timeout(30)
    async def test_send_photo_and_delete(self):
        """Send a 1x1 PNG photo and delete the message."""
        chat_id = await _resolve_chat_id()
        png_path = None
        try:
            png_data = _make_1x1_png()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(png_data)
                png_path = f.name

            async with stdio_client(_server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    msg_id = None
                    try:
                        result = await session.call_tool(
                            "telegram",
                            {
                                "action": "send_photo",
                                "chat_id": chat_id,
                                "file_path_or_url": png_path,
                                "caption": "[test] photo",
                            },
                        )
                        data = _parse(result)
                        assert isinstance(data, dict)
                        assert "error" not in data, f"Send photo failed: {data}"
                        msg_id = data.get("message_id")
                        assert msg_id is not None
                    finally:
                        if msg_id:
                            await session.call_tool(
                                "telegram",
                                {
                                    "action": "delete",
                                    "chat_id": chat_id,
                                    "message_id": msg_id,
                                },
                            )
        finally:
            if png_path and os.path.exists(png_path):
                os.unlink(png_path)

    @pytest.mark.timeout(30)
    async def test_download_not_implemented(self):
        """download in bot mode returns error (NotImplementedError)."""
        chat_id = await _resolve_chat_id()
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {
                        "action": "download_media",
                        "chat_id": chat_id,
                        "message_id": 1,
                    },
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" in data


# ---------------------------------------------------------------------------
# TestFullBotContacts
# ---------------------------------------------------------------------------


@full
@pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set")
class TestFullBotContacts:
    """Contacts operations via MCP protocol (all user-only in bot mode)."""

    @pytest.mark.timeout(30)
    async def test_contacts_list_mode_error(self):
        """contacts list in bot mode returns mode error."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "list_contacts"},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" in data

    @pytest.mark.timeout(30)
    async def test_contacts_search_mode_error(self):
        """contacts search in bot mode returns mode error."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "search_contacts", "query": "test"},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" in data


# ---------------------------------------------------------------------------
# TestFullConfig
# ---------------------------------------------------------------------------


@full
@pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set")
class TestFullConfig:
    """Config tool operations via MCP protocol."""

    @pytest.mark.timeout(30)
    async def test_config_status(self):
        """config status shows bot mode, connected."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "status"})
                data = _parse(result)
                assert isinstance(data, dict)
                assert data.get("mode") == "bot"
                assert data.get("connected") is True
                assert data.get("authorized") is True
                assert "config" in data

    @pytest.mark.timeout(30)
    async def test_config_set(self):
        """config set updates runtime config."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "config",
                    {"action": "set", "message_limit": 99},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" not in data, f"Set failed: {data}"
                assert data.get("updated", {}).get("message_limit") == 99

    @pytest.mark.timeout(30)
    async def test_config_cache_clear(self):
        """config cache_clear succeeds."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "cache_clear"})
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" not in data
                assert data.get("message") == "Cache cleared."

    @pytest.mark.timeout(30)
    async def test_config_unknown_action(self):
        """config with unknown action returns corrective error."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "nonexistent"})
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" in data
                assert "Unknown action" in data["error"]


# ---------------------------------------------------------------------------
# TestFullHelp
# ---------------------------------------------------------------------------


@full
@pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set")
class TestFullHelp:
    """Help tool operations via MCP protocol."""

    @pytest.mark.timeout(30)
    async def test_help_all(self):
        """help with no topic returns all documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {})
                data = _parse(result)
                if isinstance(data, str):
                    assert len(data) > 100, "Expected substantial docs"
                else:
                    assert "error" not in data

    @pytest.mark.timeout(30)
    async def test_help_messages(self):
        """help topic=messages returns messages documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "messages"})
                data = _parse(result)
                assert isinstance(data, str), f"Expected str, got {type(data)}"
                assert len(data) > 50

    @pytest.mark.timeout(30)
    async def test_help_chats(self):
        """help topic=chats returns chats documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "chats"})
                data = _parse(result)
                assert isinstance(data, str)
                assert len(data) > 50

    @pytest.mark.timeout(30)
    async def test_help_media(self):
        """help topic=media returns media documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "media"})
                data = _parse(result)
                assert isinstance(data, str)
                assert len(data) > 50

    @pytest.mark.timeout(30)
    async def test_help_contacts(self):
        """help topic=contacts returns contacts documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "contacts"})
                data = _parse(result)
                assert isinstance(data, str)
                assert len(data) > 50

    @pytest.mark.timeout(30)
    async def test_help_default_returns_all(self):
        """help with topic=None returns all documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": None})
                data = _parse(result)
                if isinstance(data, str):
                    assert len(data) > 100

    @pytest.mark.timeout(30)
    async def test_help_invalid_topic(self):
        """help with invalid topic returns error with suggestion."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "nonexistent"})
                data = _parse(result)
                assert isinstance(data, dict)
                assert "error" in data
                assert "Unknown topic" in data["error"]


# ---------------------------------------------------------------------------
# TestFullNoAuth
# ---------------------------------------------------------------------------


@full
class TestFullNoAuth:
    """Tools return setup hints without credentials (no bot token)."""

    @pytest.mark.timeout(30)
    async def test_telegram_send_unconfigured(self):
        """telegram send without auth returns setup hints."""
        async with stdio_client(_server_params(with_token=False)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "send", "chat_id": "123", "text": "test"},
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    @pytest.mark.timeout(30)
    async def test_telegram_list_chats_unconfigured(self):
        """telegram list_chats without auth returns setup hints."""
        async with stdio_client(_server_params(with_token=False)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("telegram", {"action": "list_chats"})
                data = _parse(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    @pytest.mark.timeout(30)
    async def test_telegram_send_photo_unconfigured(self):
        """telegram send_photo without auth returns setup hints."""
        async with stdio_client(_server_params(with_token=False)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {
                        "action": "send_photo",
                        "chat_id": "123",
                        "file_path_or_url": "/tmp/x.jpg",
                    },
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    @pytest.mark.timeout(30)
    async def test_telegram_list_contacts_unconfigured(self):
        """telegram list_contacts without auth returns setup hints."""
        async with stdio_client(_server_params(with_token=False)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram", {"action": "list_contacts"}
                )
                data = _parse(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    @pytest.mark.timeout(30)
    async def test_config_status_unconfigured(self):
        """config status without auth shows unconfigured state."""
        async with stdio_client(_server_params(with_token=False)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "status"})
                data = _parse(result)
                assert isinstance(data, dict)
                assert data.get("configured") is False
                assert data.get("connected") is False
                assert "setup" in data
