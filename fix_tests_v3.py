import os

def fix_conftest_e2e():
    path = "tests/conftest_e2e.py"
    with open(path, 'r') as f:
        content = f.read()

    old_code = """    else:
        import webbrowser

        webbrowser.open(url)"""

    new_code = """    else:
        # Skip in CI to avoid hangs
        if os.environ.get("GITHUB_ACTIONS"):
            return
        import webbrowser

        webbrowser.open(url)"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(path, 'w') as f:
            f.write(content)
        print("Fixed conftest_e2e.py")

def update_auth_client_tests():
    path = "tests/test_auth_client.py"
    content = """\"\"\"Tests for AuthClient.\"\"\"

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient, _mask_phone
from better_telegram_mcp.backends.security import SecurityError


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock(return_value={"authenticated_as": "Test User"})
    return backend


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.auth_url = "https://relay.example.com"
    settings.phone = "+1234567890"
    return settings


class TestAuthClient:
    def test_mask_phone(self):
        assert _mask_phone("1234567890") == "1234***7890"
        assert _mask_phone("1234") == "12***"

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

        mock_response = MagicMock()
        mock_response.json.return_value = {"url": "https://relay.example.com/auth", "token": "test-token"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            url = await client.create_session()

            assert url == "https://relay.example.com/auth"
            assert client._token == "test-token"
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://1.2.3.4/api/sessions"

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_poll_and_execute_completed(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)
        client._token = "test-token"

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "completed"}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch("asyncio.sleep", return_value=None):
                await client.poll_and_execute()

            assert client._auth_complete.is_set()

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_poll_and_execute_expired(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)
        client._token = "test-token"

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "expired"}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch("asyncio.sleep", return_value=None):
                await client.poll_and_execute()

            assert not client._auth_complete.is_set()

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_handle_command_send_code(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)
        client._token = "test-token"

        with patch.object(client, "_push_result", new_callable=AsyncMock) as mock_push:
            await client._handle_command({"action": "send_code"})
            mock_backend.send_code.assert_called_once_with("+1234567890")
            mock_push.assert_called_with("send_code", ok=True)

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_handle_command_verify(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)
        client._token = "test-token"

        with patch.object(client, "_push_result", new_callable=AsyncMock) as mock_push:
            await client._handle_command({"action": "verify", "code": "12345", "password": "pwd"})
            mock_backend.sign_in.assert_called_once_with("+1234567890", "12345", password="pwd")
            mock_push.assert_called_with("verify", ok=True, name="Test User")
            assert client._auth_complete.is_set()

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_push_result(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)
        client._token = "test-token"

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            await client._push_result("test_action", extra="data")
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://1.2.3.4/api/sessions/test-token/result"
            assert kwargs["json"] == {"action": "test_action", "extra": "data"}

    @pytest.mark.asyncio
    @patch("better_telegram_mcp.backends.security.validate_url")
    async def test_close(self, mock_validate, mock_backend, mock_settings):
        mock_validate.return_value = "1.2.3.4"
        client = AuthClient(mock_backend, mock_settings)
        with patch.object(client._client, "aclose", new_callable=AsyncMock) as mock_aclose:
            await client.close()
            mock_aclose.assert_called_once()
"""
    with open(path, 'w') as f:
        f.write(content)
    print("Updated test_auth_client.py with better coverage")

if __name__ == "__main__":
    fix_conftest_e2e()
    update_auth_client_tests()
