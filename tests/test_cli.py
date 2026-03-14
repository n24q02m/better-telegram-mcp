from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCliDispatch:
    def test_auth_dispatch(self):
        """CLI dispatches to run_auth when argv has 'auth'."""
        from better_telegram_mcp.__main__ import _cli

        with (
            patch.object(sys, "argv", ["prog", "auth"]),
            patch("better_telegram_mcp.cli.run_auth") as mock_auth,
        ):
            _cli()
            mock_auth.assert_called_once()

    def test_server_dispatch(self):
        """CLI dispatches to server main when no 'auth' arg."""
        from better_telegram_mcp.__main__ import _cli

        with (
            patch.object(sys, "argv", ["prog"]),
            patch("better_telegram_mcp.server.main") as mock_main,
        ):
            _cli()
            mock_main.assert_called_once()


class TestAuthAsync:
    async def test_already_authorized(self, tmp_path, monkeypatch):
        """When session is already authorized, print success and disconnect."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
        monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))

        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"

        mock_client = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        mock_client.get_me = AsyncMock(return_value=mock_me)
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        with patch("better_telegram_mcp.cli.TelegramClient", return_value=mock_client):
            await _auth_async("test_session")

        mock_client.connect.assert_awaited_once()
        mock_client.get_me.assert_awaited_once()
        mock_client.disconnect.assert_awaited_once()

    async def test_missing_credentials_exits(self, monkeypatch):
        """Exit with error when API_ID/HASH not set."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
        monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            await _auth_async()

        assert exc_info.value.code == 1

    async def test_missing_api_hash_exits(self, monkeypatch):
        """Exit with error when only API_ID is set."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)

        with pytest.raises(SystemExit):
            await _auth_async()

    async def test_session_file_permissions(self, tmp_path, monkeypatch):
        """Session file should be chmod 600 after auth."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
        monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))

        # Create a fake .session file
        session_file = tmp_path / "perms_test.session"
        session_file.write_text("fake_session")
        session_file.chmod(0o644)

        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"

        mock_client = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        mock_client.get_me = AsyncMock(return_value=mock_me)

        with patch("better_telegram_mcp.cli.TelegramClient", return_value=mock_client):
            await _auth_async("perms_test")

        assert session_file.stat().st_mode & 0o777 == 0o600

    async def test_uses_env_session_name(self, tmp_path, monkeypatch):
        """Falls back to TELEGRAM_SESSION_NAME env var."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
        monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("TELEGRAM_SESSION_NAME", "custom_session")

        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"

        mock_client = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        mock_client.get_me = AsyncMock(return_value=mock_me)

        with patch("better_telegram_mcp.cli.TelegramClient", return_value=mock_client) as cls:
            await _auth_async()  # no session_name arg

        # Should use "custom_session" from env
        call_args = cls.call_args
        session_str = call_args[0][0]
        assert "custom_session" in session_str


class TestRunAuth:
    def test_parses_session_name(self, monkeypatch):
        """run_auth parses --session-name from argv."""
        from better_telegram_mcp.cli import run_auth

        monkeypatch.setattr(sys, "argv", ["prog", "auth", "--session-name", "my_session"])

        with patch("better_telegram_mcp.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            run_auth()
            mock_asyncio.run.assert_called_once()
            # The coroutine passed to asyncio.run should be _auth_async("my_session")
            coro = mock_asyncio.run.call_args[0][0]
            assert coro is not None

    def test_parses_default_session(self, monkeypatch):
        """run_auth works without --session-name."""
        from better_telegram_mcp.cli import run_auth

        monkeypatch.setattr(sys, "argv", ["prog", "auth"])

        with patch("better_telegram_mcp.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            run_auth()
            mock_asyncio.run.assert_called_once()


class TestAuthFlow:
    async def test_not_authorized_sends_code(self, tmp_path, monkeypatch):
        """When not authorized, sends code request and signs in."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
        monkeypatch.setenv("TELEGRAM_PHONE", "+84912345678")
        monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))

        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"

        mock_client = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=False)
        mock_client.send_code_request = AsyncMock()
        mock_client.sign_in = AsyncMock()
        mock_client.get_me = AsyncMock(return_value=mock_me)

        with (
            patch("better_telegram_mcp.cli.TelegramClient", return_value=mock_client),
            patch("builtins.input", return_value="12345"),
        ):
            await _auth_async("flow_test")

        mock_client.send_code_request.assert_awaited_once_with("+84912345678")
        mock_client.sign_in.assert_awaited_once_with("+84912345678", "12345")

    async def test_2fa_with_env_password(self, tmp_path, monkeypatch):
        """When sign_in fails and password env is set, use it for 2FA."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
        monkeypatch.setenv("TELEGRAM_PHONE", "+84912345678")
        monkeypatch.setenv("TELEGRAM_PASSWORD", "my2fapass")
        monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))

        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"

        mock_client = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=False)
        mock_client.send_code_request = AsyncMock()
        mock_client.sign_in = AsyncMock(side_effect=[Exception("2FA required"), mock_me])
        mock_client.get_me = AsyncMock(return_value=mock_me)

        with (
            patch("better_telegram_mcp.cli.TelegramClient", return_value=mock_client),
            patch("builtins.input", return_value="12345"),
        ):
            await _auth_async("twofa_test")

        # First call: sign_in(phone, code) — raises
        # Second call: sign_in(password="my2fapass")
        assert mock_client.sign_in.await_count == 2

    async def test_2fa_with_input_password(self, tmp_path, monkeypatch):
        """When sign_in fails and no password env, prompt for 2FA password."""
        from better_telegram_mcp.cli import _auth_async

        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
        monkeypatch.setenv("TELEGRAM_PHONE", "+84912345678")
        monkeypatch.delenv("TELEGRAM_PASSWORD", raising=False)
        monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))

        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"

        mock_client = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=False)
        mock_client.send_code_request = AsyncMock()
        mock_client.sign_in = AsyncMock(side_effect=[Exception("2FA required"), mock_me])
        mock_client.get_me = AsyncMock(return_value=mock_me)

        # First input: code, Second input: 2FA password
        inputs = iter(["12345", "my2fapass"])

        with (
            patch("better_telegram_mcp.cli.TelegramClient", return_value=mock_client),
            patch("builtins.input", side_effect=inputs),
        ):
            await _auth_async("twofa_input_test")

        assert mock_client.sign_in.await_count == 2
