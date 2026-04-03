import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from loguru import logger

from better_telegram_mcp.auth_client import AuthClient, _mask_phone
from better_telegram_mcp.config import Settings


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock()
    return backend


@pytest.fixture
def settings():
    return Settings(phone="+1234567890", auth_url="https://auth.example.com")


class TestMaskPhone:
    def test_mask_long_phone(self):
        assert _mask_phone("+1234567890") == "+123***7890"

    def test_mask_short_phone(self):
        assert _mask_phone("12345") == "12***"


class TestAuthClient:
    @pytest.mark.asyncio
    async def test_create_session_success(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)

            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "url": "https://auth.example.com/login/123",
                "token": "abc-token",
            }
            mock_resp.raise_for_status = MagicMock()

            with patch.object(
                client._client, "post", new_callable=AsyncMock, return_value=mock_resp
            ):
                url = await client.create_session()
                assert url == "https://auth.example.com/login/123"
                assert client._token == "abc-token"

    @pytest.mark.asyncio
    async def test_poll_and_execute_http_error(self, mock_backend, settings, caplog):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"

            # Use a counter to stop the loop
            calls = 0

            async def side_effect(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise httpx.HTTPError("test error")
                client._auth_complete.set()
                mock_resp = MagicMock()
                mock_resp.json.return_value = {"status": "completed"}
                return mock_resp

            # loguru needs to be configured to capture in caplog
            logger.add(caplog.handler, format="{message}")

            with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0):
                with patch.object(client._client, "get", side_effect=side_effect):
                    await client.poll_and_execute()

            assert "HTTP error in auth request: test error" in caplog.text

    @pytest.mark.asyncio
    async def test_poll_and_execute_generic_exception(
        self, mock_backend, settings, caplog
    ):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"

            calls = 0

            async def side_effect(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise ValueError("generic error")
                client._auth_complete.set()
                mock_resp = MagicMock()
                mock_resp.json.return_value = {"status": "completed"}
                return mock_resp

            logger.add(caplog.handler, format="{message}")

            with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0):
                with patch.object(client._client, "get", side_effect=side_effect):
                    await client.poll_and_execute()

            assert "Poll error: generic error" in caplog.text

    @pytest.mark.asyncio
    async def test_poll_and_execute_command_send_code(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"

            responses = [
                {"status": "command", "action": "send_code"},
                {"status": "completed"},
            ]

            async def get_side_effect(*args, **kwargs):
                data = responses.pop(0)
                mock_resp = MagicMock()
                mock_resp.json.return_value = data
                return mock_resp

            with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0):
                with patch.object(client._client, "get", side_effect=get_side_effect):
                    with patch.object(
                        client, "_push_result", new_callable=AsyncMock
                    ) as mock_push:
                        await client.poll_and_execute()

                        mock_backend.send_code.assert_called_once_with("+1234567890")
                        mock_push.assert_called_with("send_code", ok=True)

    @pytest.mark.asyncio
    async def test_poll_and_execute_command_verify(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"

            mock_backend.sign_in.return_value = {"authenticated_as": "Test User"}

            responses = [
                {
                    "status": "command",
                    "action": "verify",
                    "code": "12345",
                    "password": "pass",
                },
                {"status": "completed"},
            ]

            async def get_side_effect(*args, **kwargs):
                data = responses.pop(0)
                mock_resp = MagicMock()
                mock_resp.json.return_value = data
                return mock_resp

            with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0):
                with patch.object(client._client, "get", side_effect=get_side_effect):
                    with patch.object(
                        client, "_push_result", new_callable=AsyncMock
                    ) as mock_push:
                        await client.poll_and_execute()

                        mock_backend.sign_in.assert_called_once_with(
                            "+1234567890", "12345", password="pass"
                        )
                        mock_push.assert_called_with(
                            "verify", ok=True, name="Test User"
                        )
                        assert client._auth_complete.is_set()

    @pytest.mark.asyncio
    async def test_poll_and_execute_expired(self, mock_backend, settings, caplog):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "expired"}

            logger.add(caplog.handler, format="{message}")

            with patch("better_telegram_mcp.auth_client.POLL_INTERVAL", 0):
                with patch.object(client._client, "get", return_value=mock_resp):
                    await client.poll_and_execute()

            assert "Auth session expired" in caplog.text

    @pytest.mark.asyncio
    async def test_wait_for_auth(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)

            # Start waiting in a task
            wait_task = asyncio.create_task(client.wait_for_auth())

            # Complete auth
            client._auth_complete.set()

            await asyncio.wait_for(wait_task, timeout=1.0)
            assert wait_task.done()

    @pytest.mark.asyncio
    async def test_close(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            with patch.object(
                client._client, "aclose", new_callable=AsyncMock
            ) as mock_aclose:
                await client.close()
                mock_aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_result_success(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"

            with patch.object(
                client._client, "post", new_callable=AsyncMock
            ) as mock_post:
                await client._push_result("test_action", some="data")
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                assert kwargs["json"] == {"action": "test_action", "some": "data"}

    @pytest.mark.asyncio
    async def test_push_result_error(self, mock_backend, settings, caplog):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"

            logger.add(caplog.handler, format="{message}")

            with patch.object(
                client._client, "post", side_effect=Exception("push fail")
            ):
                await client._push_result("test_action")

            assert "Push result error: push fail" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_command_send_code_error(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"
            mock_backend.send_code.side_effect = Exception("send fail")

            with patch.object(
                client, "_push_result", new_callable=AsyncMock
            ) as mock_push:
                await client._handle_command({"action": "send_code"})
                mock_push.assert_called_with("send_code", ok=False, error="send fail")

    @pytest.mark.asyncio
    async def test_handle_command_verify_error(self, mock_backend, settings):
        with patch("better_telegram_mcp.backends.security.validate_url"):
            client = AuthClient(mock_backend, settings)
            client._token = "abc-token"
            mock_backend.sign_in.side_effect = Exception("verify fail")

            with patch.object(
                client, "_push_result", new_callable=AsyncMock
            ) as mock_push:
                await client._handle_command({"action": "verify", "code": "12345"})
                mock_push.assert_called_with("verify", ok=False, error="verify fail")
