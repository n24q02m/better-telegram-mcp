"""Tests for AuthClient."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.auth_client import AuthClient


@pytest.fixture
def mock_backend():
    return MagicMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.auth_url = "https://relay.example.com"
    settings.phone = "+1234567890"
    return settings


class TestAuthClient:
    @patch("better_telegram_mcp.backends.security.validate_url")
    def test_init_pins_ip(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)

        assert client._pinned_base_url == "https://1.2.3.4"
        assert client._headers == {"Host": "relay.example.com"}
        assert client._extensions == {"sni_hostname": "relay.example.com"}
        mock_validate.assert_called_once_with("https://relay.example.com")

    @patch("better_telegram_mcp.backends.security.validate_url")
    def test_init_pins_ipv6(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "2001:db8::1"
        client = AuthClient(mock_backend, mock_settings)

        assert client._pinned_base_url == "https://[2001:db8::1]"
        assert client._headers == {"Host": "relay.example.com"}

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_create_session(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "url": "https://relay.example.com/auth",
            "token": "test-token",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            url = await client.create_session()

            assert url == "https://relay.example.com/auth"
            assert client._token == "test-token"
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://1.2.3.4/api/sessions"
            assert kwargs["headers"] == {"Host": "relay.example.com"}
            assert kwargs["extensions"] == {"sni_hostname": "relay.example.com"}

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_poll_and_execute_completed(
        self, mock_validate, mock_backend, mock_settings
    ):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)
        client._token = "test-token"

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "completed"}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            # Start polling in a task
            poll_task = asyncio.create_task(client.poll_and_execute())

            # Wait for auth to complete
            await asyncio.wait_for(client.wait_for_auth(), timeout=5.0)

            assert client._auth_complete.is_set()
            await poll_task
