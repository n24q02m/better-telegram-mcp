from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient
from better_telegram_mcp.config import Settings


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock(return_value={"authenticated_as": "Test User"})
    return backend


@pytest.fixture
def settings():
    return Settings(phone="1234567890", auth_url="https://relay.example.com")


@pytest.fixture
def auth_client(mock_backend, settings):
    with patch("better_telegram_mcp.auth_client.httpx.AsyncClient"):
        # We also need to mock validate_url to avoid DNS lookups
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            return client


@pytest.mark.asyncio
async def test_create_session_success(auth_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"url": "https://auth.page", "token": "test-token"}
    auth_client._client.post = AsyncMock(return_value=mock_resp)

    url = await auth_client.create_session()

    assert url == "https://auth.page"
    assert auth_client.url == "https://auth.page"
    assert auth_client._token == "test-token"
    auth_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_session_error(auth_client):
    auth_client._client.post = AsyncMock(side_effect=httpx.HTTPError("Network error"))

    with pytest.raises(httpx.HTTPError):
        await auth_client.create_session()


@pytest.mark.asyncio
async def test_poll_and_execute_expired(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "expired"}
    auth_client._client.get = AsyncMock(return_value=mock_resp)

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    assert not auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_completed(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "completed"}
    auth_client._client.get = AsyncMock(return_value=mock_resp)

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_command_send_code(auth_client, mock_backend):
    auth_client._token = "test-token"

    # First call returns command, second call returns completed to stop the loop
    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {"status": "command", "action": "send_code"}

    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    auth_client._client.get = AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done])
    auth_client._client.post = AsyncMock()

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    mock_backend.send_code.assert_called_once_with("1234567890")
    # Verify push_result was called
    auth_client._client.post.assert_called_once()
    assert auth_client._client.post.call_args[1]["json"]["ok"] is True


@pytest.mark.asyncio
async def test_poll_and_execute_command_verify(auth_client, mock_backend):
    auth_client._token = "test-token"

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
        # poll_and_execute will exit because verify success sets _auth_complete
        await auth_client.poll_and_execute()

    mock_backend.sign_in.assert_called_once_with("1234567890", "12345", password="pwd")
    auth_client._client.post.assert_called_once()
    assert auth_client._client.post.call_args[1]["json"]["name"] == "Test User"
    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_errors(auth_client):
    auth_client._token = "test-token"

    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    auth_client._client.get = AsyncMock(
        side_effect=[
            httpx.HTTPError("http error"),
            Exception("generic error"),
            mock_resp_done,
        ]
    )

    with patch("asyncio.sleep", AsyncMock()):
        await auth_client.poll_and_execute()

    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_handle_command_errors(auth_client, mock_backend):
    auth_client._token = "test-token"
    auth_client._client.post = AsyncMock()

    # send_code error
    mock_backend.send_code.side_effect = Exception("backend error")
    await auth_client._handle_command({"action": "send_code"})
    assert auth_client._client.post.call_args[1]["json"]["ok"] is False
    assert "backend error" in auth_client._client.post.call_args[1]["json"]["error"]

    # verify error
    mock_backend.sign_in.side_effect = Exception("verify error")
    await auth_client._handle_command({"action": "verify", "code": "123"})
    assert auth_client._client.post.call_args[1]["json"]["ok"] is False
    assert "verify error" in auth_client._client.post.call_args[1]["json"]["error"]


@pytest.mark.asyncio
async def test_push_result_error(auth_client):
    auth_client._token = "test-token"
    auth_client._client.post = AsyncMock(side_effect=Exception("network error"))

    # Should catch and log, not raise
    await auth_client._push_result("action", ok=True)


@pytest.mark.asyncio
async def test_wait_for_auth(auth_client):
    auth_client._auth_complete.set()
    await auth_client.wait_for_auth()


@pytest.mark.asyncio
async def test_close(auth_client):
    auth_client._client.aclose = AsyncMock()
    await auth_client.close()
    auth_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_handle_command_no_phone(auth_client, mock_backend):
    auth_client._settings.phone = None
    await auth_client._handle_command({"action": "send_code"})
    mock_backend.send_code.assert_not_called()
