import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient, _mask_phone
from better_telegram_mcp.config import Settings


def test_mask_phone():
    assert _mask_phone("1234567890") == "1234***7890"
    assert _mask_phone("1234567") == "12***"
    assert _mask_phone("12") == "12***"


@pytest.fixture
def mock_backend():
    return AsyncMock()


@pytest.fixture
def settings():
    return Settings(phone="1234567890", auth_url="https://auth.example.com")


@pytest.fixture
def auth_client(mock_backend, settings):
    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, settings)
        return client


async def test_create_session(auth_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "url": "https://auth.example.com/login",
        "token": "test-token",
    }
    mock_resp.raise_for_status = MagicMock()

    with patch.object(
        auth_client._client, "post", AsyncMock(return_value=mock_resp)
    ) as mock_post:
        url = await auth_client.create_session()
        assert url == "https://auth.example.com/login"
        assert auth_client._token == "test-token"
        mock_post.assert_called_once()


async def test_poll_and_execute_completed(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "completed"}

    with patch.object(auth_client._client, "get", AsyncMock(return_value=mock_resp)):
        with patch("asyncio.sleep", AsyncMock()):
            await auth_client.poll_and_execute()
            assert auth_client._auth_complete.is_set()


async def test_poll_and_execute_expired(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "expired"}

    with patch.object(auth_client._client, "get", AsyncMock(return_value=mock_resp)):
        with patch("asyncio.sleep", AsyncMock()):
            await auth_client.poll_and_execute()
            assert not auth_client._auth_complete.is_set()


async def test_poll_and_execute_command(auth_client):
    auth_client._token = "test-token"
    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {"status": "command", "action": "send_code"}

    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    # Mock get to return command first, then completed to exit the loop
    with patch.object(
        auth_client._client,
        "get",
        AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done]),
    ):
        with patch.object(auth_client, "_handle_command", AsyncMock()) as mock_handle:
            with patch("asyncio.sleep", AsyncMock()):
                await auth_client.poll_and_execute()
                mock_handle.assert_called_once_with(
                    {"status": "command", "action": "send_code"}
                )


async def test_poll_and_execute_http_error(auth_client):
    auth_client._token = "test-token"

    # First call raises HTTPError, second call returns completed to exit loop
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    with patch.object(
        auth_client._client,
        "get",
        AsyncMock(side_effect=[httpx.HTTPError("error"), mock_resp_done]),
    ):
        with patch("asyncio.sleep", AsyncMock()):
            await auth_client.poll_and_execute()
            # It should catch the error and continue to the next iteration
            assert auth_client._auth_complete.is_set()


async def test_poll_and_execute_exception(auth_client):
    auth_client._token = "test-token"

    # First call raises general Exception, second call returns completed to exit loop
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    with patch.object(
        auth_client._client,
        "get",
        AsyncMock(side_effect=[Exception("error"), mock_resp_done]),
    ):
        with patch("asyncio.sleep", AsyncMock()):
            await auth_client.poll_and_execute()
            assert auth_client._auth_complete.is_set()


async def test_handle_command_send_code_success(auth_client, mock_backend):
    cmd = {"action": "send_code"}
    with patch.object(auth_client, "_push_result", AsyncMock()) as mock_push:
        await auth_client._handle_command(cmd)
        mock_backend.send_code.assert_called_once_with("1234567890")
        mock_push.assert_called_once_with("send_code", ok=True)


async def test_handle_command_send_code_error(auth_client, mock_backend):
    cmd = {"action": "send_code"}
    mock_backend.send_code.side_effect = Exception("backend error")
    with patch.object(auth_client, "_push_result", AsyncMock()) as mock_push:
        await auth_client._handle_command(cmd)
        mock_push.assert_called_once_with("send_code", ok=False, error="backend error")


async def test_handle_command_verify_success(auth_client, mock_backend):
    cmd = {"action": "verify", "code": "12345", "password": "pass"}
    mock_backend.sign_in.return_value = {"authenticated_as": "Test User"}
    with patch.object(auth_client, "_push_result", AsyncMock()) as mock_push:
        await auth_client._handle_command(cmd)
        mock_backend.sign_in.assert_called_once_with(
            "1234567890", "12345", password="pass"
        )
        mock_push.assert_called_once_with("verify", ok=True, name="Test User")
        assert auth_client._auth_complete.is_set()


async def test_handle_command_verify_error(auth_client, mock_backend):
    cmd = {"action": "verify", "code": "12345"}
    mock_backend.sign_in.side_effect = Exception("sign in error")
    with patch.object(auth_client, "_push_result", AsyncMock()) as mock_push:
        await auth_client._handle_command(cmd)
        mock_push.assert_called_once_with("verify", ok=False, error="sign in error")


async def test_push_result_success(auth_client):
    auth_client._token = "test-token"
    with patch.object(auth_client._client, "post", AsyncMock()) as mock_post:
        await auth_client._push_result("test_action", extra="data")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"] == {"action": "test_action", "extra": "data"}


async def test_push_result_error(auth_client):
    auth_client._token = "test-token"
    with patch.object(
        auth_client._client, "post", AsyncMock(side_effect=Exception("push error"))
    ):
        # Should catch and log
        await auth_client._push_result("test_action")


async def test_wait_for_auth(auth_client):
    # Simulate auth completing in a task
    async def complete_auth():
        await asyncio.sleep(0.01)
        auth_client._auth_complete.set()

    asyncio.create_task(complete_auth())
    await auth_client.wait_for_auth()
    assert auth_client._auth_complete.is_set()


async def test_close(auth_client):
    with patch.object(auth_client._client, "aclose", AsyncMock()) as mock_close:
        await auth_client.close()
        mock_close.assert_called_once()
