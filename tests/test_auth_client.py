from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient
from better_telegram_mcp.config import Settings


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock()
    return backend


@pytest.fixture
def settings():
    return Settings(
        api_id=12345,
        api_hash="hash",
        phone="+1234567890",
        auth_url="http://remote-relay.com",
    )


@pytest.fixture
def auth_client(mock_backend, settings):
    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, settings)
        client._token = "test-token"
        return client


@pytest.mark.asyncio
async def test_create_session(auth_client):
    auth_client._client.post = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=lambda: {
                "url": "http://remote-relay.com/auth/123",
                "token": "new-token",
            },
        )
    )

    url = await auth_client.create_session()

    assert url == "http://remote-relay.com/auth/123"
    assert auth_client._token == "new-token"
    auth_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_poll_and_execute_completed(auth_client):
    auth_client._client.get = AsyncMock(
        return_value=MagicMock(json=lambda: {"status": "completed"})
    )

    # We need to make sure poll_and_execute breaks the loop
    with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0.01):
        await auth_client.poll_and_execute()

    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_expired(auth_client):
    auth_client._client.get = AsyncMock(
        return_value=MagicMock(json=lambda: {"status": "expired"})
    )

    with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0.01):
        await auth_client.poll_and_execute()

    assert not auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_command_and_then_complete(auth_client):
    # First return a command, then completed to break the loop
    auth_client._client.get = AsyncMock(
        side_effect=[
            MagicMock(json=lambda: {"status": "command", "action": "send_code"}),
            MagicMock(json=lambda: {"status": "completed"}),
        ]
    )
    auth_client._handle_command = AsyncMock()

    with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0.01):
        await auth_client.poll_and_execute()

    assert auth_client._handle_command.call_count == 1
    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_http_error(auth_client):
    # Raise HTTPError once, then complete
    auth_client._client.get = AsyncMock(
        side_effect=[
            httpx.HTTPError("Network error"),
            MagicMock(json=lambda: {"status": "completed"}),
        ]
    )

    with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0.01):
        await auth_client.poll_and_execute()

    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_generic_exception(auth_client):
    """Test the generic exception handler in poll_and_execute."""
    # Raise generic Exception once, then complete
    auth_client._client.get = AsyncMock(
        side_effect=[
            Exception("Unexpected crash"),
            MagicMock(json=lambda: {"status": "completed"}),
        ]
    )

    with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0.01):
        with patch("better_telegram_mcp.auth_client.logger.exception") as mock_log_exc:
            await auth_client.poll_and_execute()
            # Verify it was logged as an exception
            mock_log_exc.assert_called_once()
            assert "Unexpected error in auth request" in mock_log_exc.call_args[0][0]

    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_handle_command_send_code_success(auth_client, mock_backend):
    auth_client._push_result = AsyncMock()
    cmd = {"action": "send_code"}

    await auth_client._handle_command(cmd)

    mock_backend.send_code.assert_called_once_with("+1234567890")
    auth_client._push_result.assert_called_once_with("send_code", ok=True)


@pytest.mark.asyncio
async def test_handle_command_send_code_failure(auth_client, mock_backend):
    auth_client._push_result = AsyncMock()
    mock_backend.send_code.side_effect = Exception("Send error")
    cmd = {"action": "send_code"}

    await auth_client._handle_command(cmd)

    auth_client._push_result.assert_called_once_with(
        "send_code", ok=False, error="Send error"
    )


@pytest.mark.asyncio
async def test_handle_command_verify_success(auth_client, mock_backend):
    auth_client._push_result = AsyncMock()
    mock_backend.sign_in.return_value = {"authenticated_as": "John Doe"}
    cmd = {"action": "verify", "code": "12345", "password": "pass"}

    await auth_client._handle_command(cmd)

    mock_backend.sign_in.assert_called_once_with(
        "+1234567890", "12345", password="pass"
    )
    auth_client._push_result.assert_called_once_with("verify", ok=True, name="John Doe")
    assert auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_handle_command_verify_failure(auth_client, mock_backend):
    auth_client._push_result = AsyncMock()
    mock_backend.sign_in.side_effect = Exception("Verify error")
    cmd = {"action": "verify", "code": "12345"}

    await auth_client._handle_command(cmd)

    auth_client._push_result.assert_called_once_with(
        "verify", ok=False, error="Verify error"
    )
    assert not auth_client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_push_result_error(auth_client):
    auth_client._client.post = AsyncMock(side_effect=Exception("Push error"))

    # Should not raise
    await auth_client._push_result("test", ok=True)
    auth_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_auth(auth_client):
    auth_client._auth_complete.set()
    # Should return immediately
    await auth_client.wait_for_auth()


@pytest.mark.asyncio
async def test_close(auth_client):
    auth_client._client.aclose = AsyncMock()
    await auth_client.close()
    auth_client._client.aclose.assert_called_once()


def test_mask_phone():
    from better_telegram_mcp.auth_client import _mask_phone

    assert _mask_phone("1234567890") == "1234***7890"
    assert _mask_phone("12345") == "12***"
