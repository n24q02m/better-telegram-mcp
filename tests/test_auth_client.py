from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient
from better_telegram_mcp.config import Settings


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock(return_value={"authenticated_as": "TestUser"})
    return backend


@pytest.fixture
def settings():
    return Settings(phone="+1234567890", auth_url="http://relay.test")


@pytest.fixture
def auth_client(mock_backend, settings):
    with patch("better_telegram_mcp.backends.security.validate_url"):
        with patch("httpx.AsyncClient"):
            client = AuthClient(mock_backend, settings)
            return client


@pytest.mark.asyncio
async def test_create_session(auth_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "url": "http://relay.test/auth?token=abc",
        "token": "abc",
    }
    auth_client._client.post = AsyncMock(return_value=mock_resp)

    url = await auth_client.create_session()

    assert url == "http://relay.test/auth?token=abc"
    assert auth_client._token == "abc"
    auth_client._client.post.assert_called_once()
    args, kwargs = auth_client._client.post.call_args
    assert args[0] == "http://relay.test/api/sessions"
    assert kwargs["json"] == {"phone_masked": "+123***7890"}


@pytest.mark.asyncio
async def test_poll_and_execute_expired(auth_client):
    auth_client._token = "abc"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "expired"}
    auth_client._client.get = AsyncMock(return_value=mock_resp)

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    assert not auth_client._auth_complete.is_set()
    auth_client._client.get.assert_called_once_with(
        "http://relay.test/api/sessions/abc"
    )


@pytest.mark.asyncio
async def test_poll_and_execute_completed(auth_client):
    auth_client._token = "abc"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "completed"}
    auth_client._client.get = AsyncMock(return_value=mock_resp)

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_command_send_code(auth_client, mock_backend):
    auth_client._token = "abc"

    # 1. Command, 2. Completed (to break loop)
    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {"status": "command", "action": "send_code"}
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    auth_client._client.get = AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done])
    auth_client._client.post = AsyncMock()

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    mock_backend.send_code.assert_called_once_with("+1234567890")
    # Should push result
    auth_client._client.post.assert_called_once()
    args, kwargs = auth_client._client.post.call_args
    assert "/result" in args[0]
    assert kwargs["json"] == {"action": "send_code", "ok": True}


@pytest.mark.asyncio
async def test_poll_and_execute_command_send_code_error(auth_client, mock_backend):
    auth_client._token = "abc"
    mock_backend.send_code.side_effect = Exception("API Error")

    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {"status": "command", "action": "send_code"}
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    auth_client._client.get = AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done])
    auth_client._client.post = AsyncMock()

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    auth_client._client.post.assert_called_once()
    assert auth_client._client.post.call_args[1]["json"]["ok"] is False
    assert auth_client._client.post.call_args[1]["json"]["error"] == "API Error"


@pytest.mark.asyncio
async def test_poll_and_execute_command_verify(auth_client, mock_backend):
    auth_client._token = "abc"

    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {
        "status": "command",
        "action": "verify",
        "code": "12345",
        "password": "pwd",
    }

    auth_client._client.get = AsyncMock(return_value=mock_resp_cmd)
    auth_client._client.post = AsyncMock()

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    mock_backend.sign_in.assert_called_once_with("+1234567890", "12345", password="pwd")
    assert auth_client._auth_complete.is_set()
    auth_client._client.post.assert_called_once()
    assert auth_client._client.post.call_args[1]["json"]["name"] == "TestUser"


@pytest.mark.asyncio
async def test_poll_and_execute_command_verify_error(auth_client, mock_backend):
    auth_client._token = "abc"
    mock_backend.sign_in.side_effect = Exception("Invalid Code")

    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {
        "status": "command",
        "action": "verify",
        "code": "12345",
    }
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    auth_client._client.get = AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done])
    auth_client._client.post = AsyncMock()

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    auth_client._client.post.assert_called_once()
    assert auth_client._client.post.call_args[1]["json"]["ok"] is False


@pytest.mark.asyncio
async def test_poll_and_execute_errors(auth_client):
    auth_client._token = "abc"

    # 1. HTTPError, 2. Exception, 3. Completed
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    auth_client._client.get = AsyncMock(
        side_effect=[
            httpx.HTTPError("conn error"),
            Exception("generic error"),
            mock_resp_done,
        ]
    )

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    assert auth_client._auth_complete.is_set()
    assert auth_client._client.get.call_count == 3


@pytest.mark.asyncio
async def test_wait_for_auth(auth_client):
    auth_client._auth_complete.set()
    await auth_client.wait_for_auth()  # Should not block


@pytest.mark.asyncio
async def test_close(auth_client):
    auth_client._client.aclose = AsyncMock()
    await auth_client.close()
    auth_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_push_result_error(auth_client):
    # Test that _push_result catches exceptions (logged but not raised)
    auth_client._token = "abc"
    auth_client._client.post = AsyncMock(side_effect=Exception("network down"))
    await auth_client._push_result("test", ok=True)
    auth_client._client.post.assert_called_once()


def test_mask_phone():
    from better_telegram_mcp.utils.formatting import mask_phone as _mask_phone

    assert _mask_phone("1234567890") == "1234***7890"
    assert _mask_phone("1234567") == "12***"
