"""Tests for Typer CLI."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from better_telegram_mcp.cli import app

runner = CliRunner()


def test_server_dispatch():
    """CLI dispatches to server main by default."""
    with patch("better_telegram_mcp.server.main") as mock_main:
        result = runner.invoke(app)
        assert result.exit_code == 0
        mock_main.assert_called_once()


def test_auth_requires_phone():
    """Auth command requires phone if not in env."""
    with patch.dict("os.environ", {}, clear=True):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 1
        assert "TELEGRAM_PHONE is required" in result.stdout


def test_auth_success():
    """Terminal auth flow success."""
    with patch(
        "better_telegram_mcp.backends.user_backend.UserBackend"
    ) as mock_backend_cls:
        mock_backend = mock_backend_cls.return_value
        mock_backend.connect = AsyncMock()
        mock_backend.is_authorized = AsyncMock(return_value=False)
        mock_backend.send_code = AsyncMock()
        mock_backend.sign_in = AsyncMock(return_value={"authenticated_as": "TestUser"})
        mock_backend.disconnect = AsyncMock()

        result = runner.invoke(app, ["auth", "--phone", "+1234567890"], input="12345\n")

        assert result.exit_code == 0
        assert "Successfully authenticated as TestUser" in result.stdout
        mock_backend.connect.assert_called_once()
        mock_backend.send_code.assert_called_once_with("+1234567890")
        mock_backend.sign_in.assert_called_once_with("+1234567890", "12345")
        mock_backend.disconnect.assert_called_once()


def test_auth_relay():
    """Relay auth flow initialization."""
    with patch(
        "better_telegram_mcp.backends.user_backend.UserBackend"
    ) as mock_backend_cls:
        with patch("better_telegram_mcp.auth_client.AuthClient") as mock_client_cls:
            mock_backend = mock_backend_cls.return_value
            mock_backend.connect = AsyncMock()
            mock_backend.disconnect = AsyncMock()

            mock_client = mock_client_cls.return_value
            mock_client.create_session = AsyncMock(return_value="http://relay/auth")
            mock_client.poll_and_execute = AsyncMock()
            mock_client.wait_for_auth = AsyncMock()
            mock_client.close = AsyncMock()

            result = runner.invoke(app, ["auth-relay", "--phone", "+1234567890"])

            assert result.exit_code == 0
            assert (
                "Auth session created. Please visit: http://relay/auth" in result.stdout
            )
            mock_client.create_session.assert_called_once()
            mock_client.poll_and_execute.assert_called_once()
            mock_client.close.assert_called_once()
