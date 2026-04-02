import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from better_telegram_mcp.auth_client import AuthClient, _mask_phone


def test_mask_phone():
    assert _mask_phone("+84912345678") == "+849***5678"
    assert _mask_phone("1234") == "12***"


@pytest.mark.asyncio
async def test_auth_client_poll_exception_recovery(monkeypatch):
    """Verify that AuthClient recovery from unexpected exceptions in poll_and_execute."""
    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.auth_url = "https://example.com/auth"
    mock_settings.phone = "+1234567890"

    # Mock validate_url to avoid network calls
    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)

    client._token = "test-token"

    # Mock httpx.AsyncClient.get to return a command
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "command", "action": "send_code"}

    # Set POLL_INTERVAL to 0 for fast testing
    monkeypatch.setattr("better_telegram_mcp.auth_client.POLL_INTERVAL", 0)

    # Track how many times _handle_command is called
    call_count = 0

    async def mock_handle_command(data):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call raises an unexpected exception
            raise Exception("Boom!")
        else:
            # Second call completes the auth
            client._auth_complete.set()

    with patch.object(client, "_client") as mock_http_client:
        mock_http_client.get = AsyncMock(return_value=mock_resp)

        with patch.object(client, "_handle_command", side_effect=mock_handle_command):
            # Run poll_and_execute. It should loop twice.
            # 1st loop: _handle_command raises Exception, caught by generic except, continues.
            # 2nd loop: _handle_command sets _auth_complete, loop terminates.

            # Use wait_for to avoid infinite loop if it fails
            await asyncio.wait_for(client.poll_and_execute(), timeout=1.0)

    assert call_count == 2
    assert client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_auth_client_poll_http_error(monkeypatch):
    """Verify that AuthClient recovery from HTTPError in poll_and_execute."""
    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.auth_url = "https://example.com/auth"

    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)
    client._token = "test-token"
    monkeypatch.setattr("better_telegram_mcp.auth_client.POLL_INTERVAL", 0)

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.HTTPError("Network fail")
        else:
            client._auth_complete.set()
            return MagicMock()

    with patch.object(client, "_client") as mock_http_client:
        mock_http_client.get = AsyncMock(side_effect=mock_get)
        await asyncio.wait_for(client.poll_and_execute(), timeout=1.0)
    assert call_count == 2


@pytest.mark.asyncio
async def test_auth_client_poll_status_handling(monkeypatch):
    """Test handling of different statuses in poll_and_execute."""
    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.auth_url = "https://example.com/auth"

    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)
    client._token = "test-token"
    monkeypatch.setattr("better_telegram_mcp.auth_client.POLL_INTERVAL", 0)

    statuses = ["expired", "completed"]
    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        resp = MagicMock()
        resp.json.return_value = {"status": statuses[call_count]}
        call_count += 1
        return resp

    with patch.object(client, "_client") as mock_http_client:
        mock_http_client.get = AsyncMock(side_effect=mock_get)
        # Test expired
        await asyncio.wait_for(client.poll_and_execute(), timeout=1.0)
        assert call_count == 1

        # Test completed
        await asyncio.wait_for(client.poll_and_execute(), timeout=1.0)
        assert call_count == 2
        assert client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_auth_client_create_session():
    """Test create_session method."""
    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.auth_url = "https://example.com/auth"
    mock_settings.phone = "+1234567890"

    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"url": "https://auth.page", "token": "tok123"}
    mock_resp.raise_for_status = MagicMock()

    with patch.object(client, "_client") as mock_http_client:
        mock_http_client.post = AsyncMock(return_value=mock_resp)
        url = await client.create_session()

    assert url == "https://auth.page"
    assert client._token == "tok123"


@pytest.mark.asyncio
async def test_auth_client_handle_command_success():
    """Verify _handle_command success paths."""
    mock_backend = AsyncMock()
    mock_backend.sign_in.return_value = {"authenticated_as": "Alice"}
    mock_settings = MagicMock()
    mock_settings.phone = "+1234567890"
    mock_settings.auth_url = "https://example.com/auth"

    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)
    client._token = "test-token"

    with patch.object(client, "_push_result") as mock_push:
        await client._handle_command({"action": "send_code"})
        mock_backend.send_code.assert_awaited_once_with("+1234567890")
        mock_push.assert_any_await("send_code", ok=True)

        await client._handle_command({"action": "verify", "code": "12345"})
        mock_backend.sign_in.assert_awaited_once_with(
            "+1234567890", "12345", password=None
        )
        mock_push.assert_any_await("verify", ok=True, name="Alice")
        assert client._auth_complete.is_set()


@pytest.mark.asyncio
async def test_auth_client_handle_command_exceptions():
    """Verify _handle_command handles exceptions."""
    mock_backend = AsyncMock()
    mock_backend.send_code.side_effect = Exception("Send failed")
    mock_backend.sign_in.side_effect = Exception("Verify failed")
    mock_settings = MagicMock()
    mock_settings.phone = "+1234567890"
    mock_settings.auth_url = "https://example.com/auth"

    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)
    client._token = "test-token"

    with patch.object(client, "_push_result") as mock_push:
        await client._handle_command({"action": "send_code"})
        mock_push.assert_awaited_with("send_code", ok=False, error="Send failed")

        await client._handle_command({"action": "verify", "code": "12345"})
        mock_push.assert_awaited_with("verify", ok=False, error="Verify failed")


@pytest.mark.asyncio
async def test_auth_client_push_result_exception():
    """Verify _push_result handles network exceptions gracefully."""
    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.auth_url = "https://example.com/auth"

    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)
    client._token = "test-token"

    with patch.object(client, "_client") as mock_http_client:
        mock_http_client.post.side_effect = Exception("Network down")
        await client._push_result("test", ok=True)


@pytest.mark.asyncio
async def test_auth_client_wait_and_close():
    """Test wait_for_auth and close."""
    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.auth_url = "https://example.com/auth"

    with patch("better_telegram_mcp.backends.security.validate_url"):
        client = AuthClient(mock_backend, mock_settings)

    client._auth_complete.set()
    await client.wait_for_auth()

    with patch.object(client, "_client") as mock_http_client:
        mock_http_client.aclose = AsyncMock()
        await client.close()
        mock_http_client.aclose.assert_awaited_once()
