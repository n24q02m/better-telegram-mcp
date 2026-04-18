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
    return Settings(phone="1234567890", auth_url="https://example.com")


@pytest.fixture
def auth_client(mock_backend, settings):
    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, settings)
        yield client


@pytest.mark.asyncio
async def test_create_session(auth_client):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"url": "https://auth.page", "token": "test-token"}

    with patch.object(
        auth_client._client, "post", AsyncMock(return_value=mock_resp)
    ) as mock_post:
        url = await auth_client.create_session()

        assert url == "https://auth.page"
        assert auth_client.url == "https://auth.page"
        assert auth_client._token == "test-token"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_poll_and_execute_expired(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "expired"}

    with (
        patch.object(auth_client._client, "get", AsyncMock(return_value=mock_resp)),
        patch("asyncio.sleep", AsyncMock()),
    ):
        await auth_client.poll_and_execute()
        assert not auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_completed(auth_client):
    auth_client._token = "test-token"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "completed"}

    with (
        patch.object(auth_client._client, "get", AsyncMock(return_value=mock_resp)),
        patch("asyncio.sleep", AsyncMock()),
    ):
        await auth_client.poll_and_execute()
        assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_send_code(auth_client, mock_backend):
    auth_client._token = "test-token"

    # First call returns command, second returns completed to break loop
    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {"status": "command", "action": "send_code"}

    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    with (
        patch.object(
            auth_client._client,
            "get",
            AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done]),
        ),
        patch.object(auth_client._client, "post", AsyncMock()) as mock_post,
        patch("asyncio.sleep", AsyncMock()),
    ):
        await auth_client.poll_and_execute()

        mock_backend.send_code.assert_called_once_with("1234567890")
        # Check push_result call
        mock_post.assert_called_with(
            "https://example.com/api/sessions/test-token/result",
            json={"action": "send_code", "ok": True},
        )


@pytest.mark.asyncio
async def test_poll_and_execute_send_code_error(auth_client, mock_backend):
    auth_client._token = "test-token"
    mock_backend.send_code.side_effect = Exception("failed to send")

    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {"status": "command", "action": "send_code"}
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    with (
        patch.object(
            auth_client._client,
            "get",
            AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done]),
        ),
        patch.object(auth_client._client, "post", AsyncMock()) as mock_post,
        patch("asyncio.sleep", AsyncMock()),
    ):
        await auth_client.poll_and_execute()

        mock_post.assert_called_with(
            "https://example.com/api/sessions/test-token/result",
            json={"action": "send_code", "ok": False, "error": "failed to send"},
        )


@pytest.mark.asyncio
async def test_poll_and_execute_verify(auth_client, mock_backend):
    auth_client._token = "test-token"

    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {
        "status": "command",
        "action": "verify",
        "code": "12345",
        "password": "pwd",
    }

    with (
        patch.object(auth_client._client, "get", AsyncMock(return_value=mock_resp_cmd)),
        patch.object(auth_client._client, "post", AsyncMock()) as mock_post,
        patch("asyncio.sleep", AsyncMock()),
    ):
        # We need to stop the loop, or it will poll forever
        # _handle_command for verify sets auth_complete if successful
        await auth_client.poll_and_execute()

        mock_backend.sign_in.assert_called_once_with(
            "1234567890", "12345", password="pwd"
        )
        mock_post.assert_called_with(
            "https://example.com/api/sessions/test-token/result",
            json={"action": "verify", "ok": True, "name": "Test User"},
        )
        assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_verify_error(auth_client, mock_backend):
    auth_client._token = "test-token"
    mock_backend.sign_in.side_effect = Exception("invalid code")

    mock_resp_cmd = MagicMock()
    mock_resp_cmd.json.return_value = {
        "status": "command",
        "action": "verify",
        "code": "12345",
    }
    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    with (
        patch.object(
            auth_client._client,
            "get",
            AsyncMock(side_effect=[mock_resp_cmd, mock_resp_done]),
        ),
        patch.object(auth_client._client, "post", AsyncMock()) as mock_post,
        patch("asyncio.sleep", AsyncMock()),
    ):
        await auth_client.poll_and_execute()

        mock_post.assert_called_with(
            "https://example.com/api/sessions/test-token/result",
            json={"action": "verify", "ok": False, "error": "invalid code"},
        )


@pytest.mark.asyncio
async def test_poll_and_execute_http_error(auth_client):
    auth_client._token = "test-token"

    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    with (
        patch.object(
            auth_client._client,
            "get",
            AsyncMock(side_effect=[httpx.HTTPError("oops"), mock_resp_done]),
        ),
        patch("asyncio.sleep", AsyncMock()),
    ):
        await auth_client.poll_and_execute()
        assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_generic_exception(auth_client):
    auth_client._token = "test-token"

    mock_resp_done = MagicMock()
    mock_resp_done.json.return_value = {"status": "completed"}

    with (
        patch.object(
            auth_client._client,
            "get",
            AsyncMock(side_effect=[Exception("boom"), mock_resp_done]),
        ),
        patch("asyncio.sleep", AsyncMock()),
    ):
        await auth_client.poll_and_execute()
        assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_push_result_error(auth_client):
    auth_client._token = "test-token"
    with patch.object(
        auth_client._client, "post", AsyncMock(side_effect=Exception("post failed"))
    ):
        # Should catch exception and log it (we just check it doesn't raise)
        await auth_client._push_result("test", ok=True)


@pytest.mark.asyncio
async def test_wait_for_auth(auth_client):
    auth_client._auth_complete.set()
    await auth_client.wait_for_auth()  # Should return immediately


@pytest.mark.asyncio
async def test_close(auth_client):
    with patch.object(auth_client._client, "aclose", AsyncMock()) as mock_aclose:
        await auth_client.close()
        mock_aclose.assert_called_once()


def test_mask_phone_util():
    from better_telegram_mcp.auth_client import _mask_phone

    assert _mask_phone("1234567890") == "1234***7890"
    assert _mask_phone("1234567") == "12***"
