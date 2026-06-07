from unittest.mock import MagicMock, patch

import pytest

from better_telegram_mcp.server import chat
from better_telegram_mcp.tools.chats import ChatOptions


@pytest.mark.asyncio
async def test_chat_error_handling():
    """Test that server.chat correctly catches and returns exceptions as strings."""

    # Mock ChatOptions
    options = ChatOptions(action="list")

    # Mock handle_chats to raise an exception
    with patch("better_telegram_mcp.server.handle_chats", side_effect=Exception("Test error")):
        # Mock get_backend to avoid initialization issues
        with patch("better_telegram_mcp.server.get_backend", return_value=MagicMock()):
            # Mock _unconfigured and _pending_auth
            with patch("better_telegram_mcp.server._unconfigured", False),                  patch("better_telegram_mcp.server._pending_auth", False):

                result = await chat(options)
                assert result == "Test error"

@pytest.mark.asyncio
async def test_chat_backend_init_error():
    """Test that server.chat handles errors during backend initialization."""

    options = ChatOptions(action="list")

    # Mock get_backend to raise an exception
    with patch("better_telegram_mcp.server.get_backend", side_effect=RuntimeError("Backend not initialized")):
        with patch("better_telegram_mcp.server._unconfigured", False),              patch("better_telegram_mcp.server._pending_auth", False):

            result = await chat(options)
            assert result == "Backend not initialized"
