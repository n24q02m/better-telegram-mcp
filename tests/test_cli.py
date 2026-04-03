"""Tests for CLI using Typer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from better_telegram_mcp.cli import app

runner = CliRunner()


class TestCli:
    def test_run_stdio(self):
        """Test 'run' command with default stdio transport."""
        with patch("better_telegram_mcp.server.mcp.run") as mock_run:
            result = runner.invoke(app, ["run"])
            assert result.exit_code == 0
            mock_run.assert_called_once_with(transport="stdio")

    def test_run_http(self):
        """Test 'run --transport http' command."""
        with patch("better_telegram_mcp.transports.http.start_http") as mock_start_http:
            result = runner.invoke(app, ["run", "--transport", "http"])
            assert result.exit_code == 0
            mock_start_http.assert_called_once()

    def test_auth_already_authorized(self):
        """Test 'auth' command when already authorized."""
        with patch(
            "better_telegram_mcp.backends.user_backend.UserBackend"
        ) as mock_backend_cls:
            mock_backend = mock_backend_cls.return_value
            mock_backend.connect = AsyncMock()
            mock_backend.is_authorized = AsyncMock(return_value=True)
            mock_backend.disconnect = AsyncMock()

            result = runner.invoke(app, ["auth"])
            assert result.exit_code == 0
            assert "Already authorized" in result.stdout

    def test_auth_interactive(self):
        """Test 'auth' command with interactive OTP input."""
        with patch(
            "better_telegram_mcp.backends.user_backend.UserBackend"
        ) as mock_backend_cls:
            mock_backend = mock_backend_cls.return_value
            mock_backend.connect = AsyncMock()
            mock_backend.is_authorized = AsyncMock(return_value=False)
            mock_backend.send_code = AsyncMock()
            mock_backend.sign_in = AsyncMock(
                return_value={"authenticated_as": "TestUser"}
            )
            mock_backend.disconnect = AsyncMock()

            # Input: phone number, then OTP code
            result = runner.invoke(app, ["auth"], input="+1234567890\n12345\n")
            assert result.exit_code == 0
            assert "Successfully authenticated as TestUser" in result.stdout
            mock_backend.send_code.assert_called_once_with("+1234567890")
            mock_backend.sign_in.assert_called_once_with("+1234567890", "12345")

    def test_auth_relay(self):
        """Test 'auth-relay' command."""
        with (
            patch(
                "better_telegram_mcp.backends.user_backend.UserBackend"
            ) as mock_backend_cls,
            patch("better_telegram_mcp.auth_client.AuthClient") as mock_client_cls,
        ):
            mock_backend = mock_backend_cls.return_value
            mock_backend.connect = AsyncMock()
            mock_backend.disconnect = AsyncMock()

            mock_client = mock_client_cls.return_value
            mock_client.create_session = AsyncMock(return_value="http://relay/auth")
            mock_client.poll_and_execute = AsyncMock()
            mock_client.wait_for_auth = AsyncMock()
            mock_client.close = AsyncMock()

            with patch("webbrowser.open") as mock_open:
                result = runner.invoke(app, ["auth-relay"])
                assert result.exit_code == 0
                assert "Relay auth required" in result.stdout
                assert "http://relay/auth" in result.stdout
                mock_open.assert_called_once_with("http://relay/auth")
                mock_client.wait_for_auth.assert_called_once()
