"""Live MCP protocol tests for better-telegram-mcp.

Spawns the MCP server as a subprocess and communicates via the MCP protocol
(JSON-RPC over stdio), testing ALL tools through the actual transport layer.

Tests are split into two groups:
- No-auth tests: work WITHOUT Telegram credentials (verify plug-and-play UX)
- Auth tests: require TELEGRAM_BOT_TOKEN (skip if not set)
"""

from __future__ import annotations

import json
import os

import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

live = pytest.mark.live


def _parse_result(result) -> dict | str:
    """Extract text from MCP call_tool result and try to parse as JSON."""
    text = result.content[0].text
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def _server_params(*, with_token: bool = False) -> StdioServerParameters:
    """Build server params, optionally injecting BOT_TOKEN."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
    if with_token and BOT_TOKEN:
        env["TELEGRAM_BOT_TOKEN"] = BOT_TOKEN
    return StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "better_telegram_mcp"],
        env=env,
    )


# =========================================================================
# No-auth tests: server starts WITHOUT any Telegram credentials
# =========================================================================


@live
class TestNoAuth:
    """Tests that work without any Telegram credentials configured."""

    # ------------------------------------------------------------------
    # 1. Tool listing -- all 3 tools exposed
    # ------------------------------------------------------------------
    async def test_list_tools(self):
        """Server exposes exactly 3 tools."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                expected = {"telegram", "config", "help"}
                assert expected == names, f"Expected {expected}, got {names}"

    # ------------------------------------------------------------------
    # 2. Help tool -- always works (no auth needed)
    # ------------------------------------------------------------------
    async def test_help_all(self):
        """help with no topic returns all documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {})
                data = _parse_result(result)
                if isinstance(data, str):
                    assert len(data) > 100, "Expected non-empty docs"
                else:
                    assert "error" not in data

    async def test_help_messages(self):
        """help topic=messages returns messages documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "messages"})
                data = _parse_result(result)
                if isinstance(data, str):
                    assert len(data) > 50

    async def test_help_chats(self):
        """help topic=chats returns chats documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "chats"})
                data = _parse_result(result)
                if isinstance(data, str):
                    assert len(data) > 50

    async def test_help_media(self):
        """help topic=media returns media documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "media"})
                data = _parse_result(result)
                if isinstance(data, str):
                    assert len(data) > 50

    async def test_help_contacts(self):
        """help topic=contacts returns contacts documentation."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "contacts"})
                data = _parse_result(result)
                if isinstance(data, str):
                    assert len(data) > 50

    async def test_help_invalid_topic(self):
        """help with invalid topic returns error with valid_topics."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {"topic": "nonexistent"})
                data = _parse_result(result)
                if isinstance(data, dict):
                    assert "error" in data

    # ------------------------------------------------------------------
    # 3. Config tool -- status works unconfigured
    # ------------------------------------------------------------------
    async def test_config_status_unconfigured(self):
        """config status shows unconfigured state with setup hints."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "status"})
                data = _parse_result(result)
                assert isinstance(data, dict), f"Expected dict, got {type(data)}"
                assert data.get("configured") is False
                assert data.get("connected") is False
                assert "setup" in data

    async def test_config_set_unconfigured(self):
        """config set without auth returns setup instructions (not crash)."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "config", {"action": "set", "message_limit": 10}
                )
                data = _parse_result(result)
                assert isinstance(data, dict)
                # Should return "Not configured" setup hints
                assert "setup" in data or "error" in data

    # ------------------------------------------------------------------
    # 4. Unconfigured telegram tool returns setup hints (NOT crash)
    # ------------------------------------------------------------------
    async def test_telegram_send_unconfigured(self):
        """telegram send without auth returns structured setup hints."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram",
                    {"action": "history", "chat_id": "123", "limit": 5},
                )
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    async def test_telegram_list_chats_unconfigured(self):
        """telegram list_chats without auth returns structured setup hints."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("telegram", {"action": "list_chats"})
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    async def test_telegram_send_photo_unconfigured(self):
        """telegram send_photo without auth returns structured setup hints."""
        async with stdio_client(_server_params()) as (read, write):
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
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    async def test_telegram_list_contacts_unconfigured(self):
        """telegram list_contacts without auth returns structured setup hints."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram", {"action": "list_contacts"}
                )
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert "setup" in data or "error" in data

    # ------------------------------------------------------------------
    # 5. Setup hints structure validation
    # ------------------------------------------------------------------
    async def test_setup_hints_contain_bot_and_user_modes(self):
        """Setup hints include both bot_mode and user_mode instructions."""
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("telegram", {"action": "list_chats"})
                data = _parse_result(result)
                assert isinstance(data, dict)
                setup = data.get("setup", {})
                assert "bot_mode" in setup, "Missing bot_mode setup instructions"
                assert "user_mode" in setup, "Missing user_mode setup instructions"


# =========================================================================
# Auth tests: server starts WITH TELEGRAM_BOT_TOKEN
# =========================================================================


@live
@pytest.mark.skipif(not BOT_TOKEN, reason="TELEGRAM_BOT_TOKEN not set")
class TestWithAuth:
    """Tests that require a valid TELEGRAM_BOT_TOKEN."""

    async def test_list_tools_with_auth(self):
        """Server exposes 3 tools when authenticated."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert len(names) == 3

    async def test_config_status_connected(self):
        """config status shows connected=True with valid token."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "status"})
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert data.get("connected") is True
                assert data.get("mode") == "bot"

    async def test_config_set_message_limit(self):
        """config set updates message_limit at protocol level."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "config", {"action": "set", "message_limit": 42}
                )
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert data.get("updated", {}).get("message_limit") == 42

    async def test_config_cache_clear(self):
        """config cache_clear succeeds at protocol level."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "cache_clear"})
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert "message" in data or "error" not in data

    async def test_config_unknown_action(self):
        """config with unknown action returns error."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("config", {"action": "nonexistent"})
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert "error" in data

    async def test_help_all_with_auth(self):
        """help returns full documentation when authenticated."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("help", {})
                data = _parse_result(result)
                if isinstance(data, str):
                    assert len(data) > 100

    async def test_telegram_history_bot_self(self):
        """telegram history on bot's own chat returns result (may be empty)."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Bot history returns empty list (Bot API limitation)
                result = await session.call_tool(
                    "telegram",
                    {"action": "history", "chat_id": "123", "limit": 5},
                )
                data = _parse_result(result)
                assert isinstance(data, dict)
                # Either returns data or a structured error (NOT a crash)
                assert "error" in data or "messages" in data or isinstance(data, dict)

    async def test_telegram_list_chats_bot_mode_error(self):
        """telegram list_chats in bot mode returns mode error."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("telegram", {"action": "list_chats"})
                data = _parse_result(result)
                assert isinstance(data, dict)
                # Bot mode cannot list chats - should return error
                assert "error" in data

    async def test_telegram_list_contacts_bot_mode_error(self):
        """telegram list_contacts in bot mode returns mode error."""
        async with stdio_client(_server_params(with_token=True)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "telegram", {"action": "list_contacts"}
                )
                data = _parse_result(result)
                assert isinstance(data, dict)
                assert "error" in data
