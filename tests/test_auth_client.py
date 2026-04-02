from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient, _mask_phone
from better_telegram_mcp.config import Settings


def test_mask_phone():
    assert _mask_phone("123456789") == "1234***6789"
    assert _mask_phone("1234567") == "12***"
    assert _mask_phone("12") == "12***"
    assert _mask_phone("1") == "1***"


@pytest.fixture
def settings():
    return Settings(phone="+1234567890", auth_url="https://auth.example.com")


@pytest.fixture
def auth_client(mock_user_backend, settings):
    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_user_backend, settings)
        return client


class TestAuthClient:
    async def test_create_session(self, auth_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "url": "https://auth.example.com/start",
            "token": "test-token",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(
            auth_client._client, "post", new_callable=AsyncMock, return_value=mock_resp
        ) as mock_post:
            url = await auth_client.create_session()

            assert url == "https://auth.example.com/start"
            assert auth_client._token == "test-token"
            mock_post.assert_called_once()

    async def test_poll_and_execute_http_error(self, auth_client):
        """Test that httpx.HTTPError is handled in poll_and_execute."""
        auth_client._token = "test-token"

        # We want it to loop once, hit the error, then we stop it
        # Side effect returns the error once, then we set event to stop
        async def side_effect(*args, **kwargs):
            auth_client._auth_complete.set()
            raise httpx.HTTPError("Network error")

        with (
            patch.object(
                auth_client._client,
                "get",
                new_callable=AsyncMock,
                side_effect=side_effect,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            await auth_client.poll_and_execute()
            mock_sleep.assert_called()

    async def test_poll_and_execute_generic_exception(self, auth_client):
        """Test that generic Exception is handled in poll_and_execute."""
        auth_client._token = "test-token"

        async def side_effect(*args, **kwargs):
            auth_client._auth_complete.set()
            raise Exception("Unexpected error")

        with (
            patch.object(
                auth_client._client,
                "get",
                new_callable=AsyncMock,
                side_effect=side_effect,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await auth_client.poll_and_execute()

    async def test_poll_and_execute_expired(self, auth_client):
        auth_client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "expired"}

        with (
            patch.object(
                auth_client._client,
                "get",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await auth_client.poll_and_execute()
            assert not auth_client._auth_complete.is_set()

    async def test_poll_and_execute_completed(self, auth_client):
        auth_client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "completed"}

        with (
            patch.object(
                auth_client._client,
                "get",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await auth_client.poll_and_execute()
            assert auth_client._auth_complete.is_set()

    async def test_poll_and_execute_command_send_code(
        self, auth_client, mock_user_backend
    ):
        auth_client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "command", "action": "send_code"}

        # To avoid infinite loop, we make second call return completed
        mock_resp_comp = MagicMock()
        mock_resp_comp.json.return_value = {"status": "completed"}

        with (
            patch.object(
                auth_client._client,
                "get",
                new_callable=AsyncMock,
                side_effect=[mock_resp, mock_resp_comp],
            ),
            patch.object(
                auth_client, "_push_result", new_callable=AsyncMock
            ) as mock_push,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await auth_client.poll_and_execute()
            mock_user_backend.send_code.assert_called_once_with(
                auth_client._settings.phone
            )
            mock_push.assert_called_once_with("send_code", ok=True)

    async def test_poll_and_execute_command_verify(
        self, auth_client, mock_user_backend
    ):
        auth_client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "command",
            "action": "verify",
            "code": "12345",
            "password": "pass",
        }

        # To avoid infinite loop, we make second call return completed
        mock_resp_comp = MagicMock()
        mock_resp_comp.json.return_value = {"status": "completed"}

        with (
            patch.object(
                auth_client._client,
                "get",
                new_callable=AsyncMock,
                side_effect=[mock_resp, mock_resp_comp],
            ),
            patch.object(
                auth_client, "_push_result", new_callable=AsyncMock
            ) as mock_push,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await auth_client.poll_and_execute()
            mock_user_backend.sign_in.assert_called_once_with(
                auth_client._settings.phone, "12345", password="pass"
            )
            mock_push.assert_called_once_with("verify", ok=True, name="Test")

    async def test_handle_command_error_send_code(self, auth_client, mock_user_backend):
        mock_user_backend.send_code.side_effect = Exception("Backend error")

        with patch.object(
            auth_client, "_push_result", new_callable=AsyncMock
        ) as mock_push:
            await auth_client._handle_command({"action": "send_code"})
            mock_push.assert_called_once_with(
                "send_code", ok=False, error="Backend error"
            )

    async def test_handle_command_error_verify(self, auth_client, mock_user_backend):
        mock_user_backend.sign_in.side_effect = Exception("Sign in error")

        with patch.object(
            auth_client, "_push_result", new_callable=AsyncMock
        ) as mock_push:
            await auth_client._handle_command({"action": "verify", "code": "123"})
            mock_push.assert_called_once_with("verify", ok=False, error="Sign in error")

    async def test_push_result_error(self, auth_client):
        """Test that exception in _push_result is caught."""
        auth_client._token = "test-token"
        with patch.object(
            auth_client._client,
            "post",
            new_callable=AsyncMock,
            side_effect=Exception("Post error"),
        ):
            # Should not raise
            await auth_client._push_result("test_action", ok=True)

    async def test_wait_for_auth(self, auth_client):
        auth_client._auth_complete.set()
        await auth_client.wait_for_auth()  # Should return immediately

    async def test_close(self, auth_client):
        with patch.object(
            auth_client._client, "aclose", new_callable=AsyncMock
        ) as mock_close:
            await auth_client.close()
            mock_close.assert_called_once()
