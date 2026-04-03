from unittest.mock import ANY as ANY_EXCEPTION
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient, _mask_phone
from better_telegram_mcp.config import Settings


@pytest.fixture
def settings():
    return Settings(
        phone="+1234567890",
        auth_url="https://auth.example.com",
        api_id=12345,
        api_hash="hash",
    )


@pytest.fixture
def auth_client(mock_user_backend, settings):
    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_user_backend, settings)
        return client


def test_mask_phone():
    assert _mask_phone("+1234567890") == "+123***7890"
    assert _mask_phone("12345") == "12***"


async def test_auth_client_init(mock_user_backend, settings):
    with patch("better_telegram_mcp.backends.security.validate_url") as mock_val:
        client = AuthClient(mock_user_backend, settings)
        mock_val.assert_called_once_with("https://auth.example.com")
        assert client._base_url == "https://auth.example.com"
        assert isinstance(client._client, httpx.AsyncClient)


async def test_create_session(auth_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "url": "https://auth.example.com/login",
        "token": "test-token",
    }
    mock_resp.raise_for_status = MagicMock()

    with patch.object(auth_client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        url = await auth_client.create_session()

        assert url == "https://auth.example.com/login"
        assert auth_client.url == "https://auth.example.com/login"
        assert auth_client._token == "test-token"
        mock_post.assert_called_once()


async def test_poll_and_execute_generic_exception(auth_client):
    """Test that generic exceptions in the poll loop are caught and logged."""
    auth_client._token = "test-token"

    # Mock response for the poll request
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "command", "action": "send_code"}

    with (
        patch.object(auth_client._client, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            auth_client, "_handle_command", side_effect=Exception("Test Exception")
        ),
        patch.object(auth_client._auth_complete, "is_set", side_effect=[False, True]),
        patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0),
        patch("better_telegram_mcp.auth_client.logger.exception") as mock_log_exc,
    ):
        mock_get.return_value = mock_resp

        await auth_client.poll_and_execute()

        # Verify logger.exception was called with the expected message
        mock_log_exc.assert_called_once_with(
            "Unexpected error in auth request: {}", ANY_EXCEPTION
        )


async def test_poll_and_execute_http_error(auth_client):
    auth_client._token = "test-token"

    with (
        patch.object(
            auth_client._client, "get", side_effect=httpx.HTTPError("Network Issue")
        ),
        patch.object(auth_client._auth_complete, "is_set", side_effect=[False, True]),
        patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0),
        patch("better_telegram_mcp.auth_client.logger.debug") as mock_log,
    ):
        await auth_client.poll_and_execute()
        mock_log.assert_called_with("Poll error: {}", ANY_EXCEPTION)


async def test_poll_and_execute_expired(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "expired"}

    with (
        patch.object(auth_client._client, "get", new_callable=AsyncMock) as mock_get,
        patch.object(auth_client._auth_complete, "is_set", side_effect=[False, True]),
        patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0),
    ):
        mock_get.return_value = mock_resp
        await auth_client.poll_and_execute()
        mock_get.assert_called_once()


async def test_poll_and_execute_completed(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "completed"}

    with (
        patch.object(auth_client._client, "get", new_callable=AsyncMock) as mock_get,
        patch.object(auth_client._auth_complete, "is_set", side_effect=[False, True]),
        patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0),
    ):
        mock_get.return_value = mock_resp
        await auth_client.poll_and_execute()
        assert auth_client._auth_complete.is_set()


async def test_handle_command_send_code(auth_client, mock_user_backend):
    auth_client._token = "test-token"
    cmd = {"action": "send_code"}

    with patch.object(auth_client, "_push_result", new_callable=AsyncMock) as mock_push:
        await auth_client._handle_command(cmd)
        mock_user_backend.send_code.assert_called_once_with("+1234567890")
        mock_push.assert_called_once_with("send_code", ok=True)


async def test_handle_command_send_code_error(auth_client, mock_user_backend):
    auth_client._token = "test-token"
    cmd = {"action": "send_code"}
    mock_user_backend.send_code.side_effect = Exception("Backend Error")

    with patch.object(auth_client, "_push_result", new_callable=AsyncMock) as mock_push:
        await auth_client._handle_command(cmd)
        mock_push.assert_called_once_with("send_code", ok=False, error="Backend Error")


async def test_handle_command_verify(auth_client, mock_user_backend):
    auth_client._token = "test-token"
    cmd = {"action": "verify", "code": "12345", "password": "pass"}
    mock_user_backend.sign_in.return_value = {"authenticated_as": "Test User"}

    with patch.object(auth_client, "_push_result", new_callable=AsyncMock) as mock_push:
        await auth_client._handle_command(cmd)
        mock_user_backend.sign_in.assert_called_once_with(
            "+1234567890", "12345", password="pass"
        )
        mock_push.assert_called_once_with("verify", ok=True, name="Test User")
        assert auth_client._auth_complete.is_set()


async def test_handle_command_verify_error(auth_client, mock_user_backend):
    auth_client._token = "test-token"
    cmd = {"action": "verify", "code": "12345"}
    mock_user_backend.sign_in.side_effect = Exception("Invalid Code")

    with patch.object(auth_client, "_push_result", new_callable=AsyncMock) as mock_push:
        await auth_client._handle_command(cmd)
        mock_push.assert_called_once_with("verify", ok=False, error="Invalid Code")


async def test_push_result_exception(auth_client):
    auth_client._token = "test-token"
    with (
        patch.object(
            auth_client._client, "post", side_effect=Exception("Network Error")
        ),
        patch("better_telegram_mcp.auth_client.logger.debug") as mock_log,
    ):
        await auth_client._push_result("test", foo="bar")
        mock_log.assert_called()


async def test_wait_for_auth(auth_client):
    auth_client._auth_complete.set()
    await auth_client.wait_for_auth()  # Should not block


async def test_close(auth_client):
    with patch.object(
        auth_client._client, "aclose", new_callable=AsyncMock
    ) as mock_close:
        await auth_client.close()
        mock_close.assert_called_once()
