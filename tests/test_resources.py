from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.resources import register_resources


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    # Mock the decorator behavior: @mcp.resource(uri) returns a decorator that returns the function
    mcp.resource.side_effect = lambda uri: lambda fn: fn
    return mcp


def test_register_resources_calls_decorator(mock_mcp):
    """Test that register_resources registers all expected URIs."""
    register_resources(mock_mcp)

    expected_uris = [
        "telegram://docs/messages",
        "telegram://docs/chats",
        "telegram://docs/media",
        "telegram://docs/contacts",
        "telegram://stats",
    ]

    # Get all URIs passed to mcp.resource
    registered_uris = [call.args[0] for call in mock_mcp.resource.call_args_list]

    for uri in expected_uris:
        assert uri in registered_uris


@pytest.mark.asyncio
async def test_resource_functions_call_help_tool(mock_mcp):
    """Test that each registered resource function calls handle_help with the right topic."""
    # We need to capture the functions being registered
    registrations = {}

    def mock_resource(uri):
        def decorator(fn):
            registrations[uri] = fn
            return fn

        return decorator

    mock_mcp.resource.side_effect = mock_resource

    register_resources(mock_mcp)

    # Patch handle_help where it's defined because it's imported locally inside the functions
    with patch(
        "better_telegram_mcp.tools.help_tool.handle_help", new_callable=AsyncMock
    ) as mock_handle:
        mock_handle.return_value = "Mocked Help Content"

        # Test each registration
        test_cases = [
            ("telegram://docs/messages", "messages"),
            ("telegram://docs/chats", "chats"),
            ("telegram://docs/media", "media"),
            ("telegram://docs/contacts", "contacts"),
            ("telegram://stats", "all"),
        ]

        for uri, expected_topic in test_cases:
            mock_handle.reset_mock()
            fn = registrations[uri]
            result = await fn()

            assert result == "Mocked Help Content"
            mock_handle.assert_called_once_with(expected_topic)
