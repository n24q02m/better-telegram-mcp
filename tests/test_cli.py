"""Tests for CLI entry point."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from better_telegram_mcp.cli import app
from better_telegram_mcp.config import Settings

runner = CliRunner()


class TestCliDispatch:
    def test_run_command(self):
        """CLI run command dispatches to server main."""
        with patch("better_telegram_mcp.server.main") as mock_main:
            result = runner.invoke(app, ["run"])
            assert result.exit_code == 0
            mock_main.assert_called_once()

    def test_default_command(self):
        """CLI without arguments dispatches to run command (server main)."""
        with patch("better_telegram_mcp.server.main") as mock_main:
            result = runner.invoke(app, [])
            assert result.exit_code == 0
            mock_main.assert_called_once()

    def test_auth_command_already_authorized(self):
        """Auth command when already authorized."""
        mock_backend = AsyncMock()
        mock_backend.is_authorized.return_value = True

        mock_client = MagicMock()
        # Mock get_me as a simple mock that returns another mock
        mock_me = MagicMock(first_name="Test")
        mock_client.get_me = AsyncMock(return_value=mock_me)

        # This is where the error likely comes from: UserBackend._ensure_client()
        # returning the AsyncMock instead of the MagicMock we want.
        mock_backend._ensure_client = MagicMock(return_value=mock_client)

        real_settings = Settings(phone="+84912345678")

        with patch("better_telegram_mcp.cli.Settings", return_value=real_settings):
            with patch(
                "better_telegram_mcp.cli.UserBackend", return_value=mock_backend
            ):
                result = runner.invoke(app, ["auth", "--phone", "+84912345678"])
                assert result.exit_code == 0
                assert "Already authorized as Test!" in result.stdout

    def test_auth_command_success(self):
        """Auth command success flow."""
        mock_backend = AsyncMock()
        mock_backend.is_authorized.return_value = False
        mock_backend.sign_in.return_value = {"authenticated_as": "Test User"}

        real_settings = Settings(phone="+84912345678")

        with patch("better_telegram_mcp.cli.Settings", return_value=real_settings):
            with patch(
                "better_telegram_mcp.cli.UserBackend", return_value=mock_backend
            ):
                with patch("typer.prompt", side_effect=["12345"]):
                    result = runner.invoke(app, ["auth", "--phone", "+84912345678"])
                    assert result.exit_code == 0
                    assert "Successfully authenticated as Test User!" in result.stdout
                    mock_backend.send_code.assert_called_once_with("+84912345678")
                    mock_backend.sign_in.assert_called_once_with(
                        "+84912345678", "12345"
                    )

    def test_auth_command_2fa(self):
        """Auth command flow with 2FA."""
        mock_backend = AsyncMock()
        mock_backend.is_authorized.return_value = False
        # First sign_in fails with 2FA required, second succeeds
        mock_backend.sign_in.side_effect = [
            Exception("SessionPasswordNeeded"),
            {"authenticated_as": "Test User"},
        ]

        real_settings = Settings(phone="+84912345678")

        with patch("better_telegram_mcp.cli.Settings", return_value=real_settings):
            with patch(
                "better_telegram_mcp.cli.UserBackend", return_value=mock_backend
            ):
                with patch("typer.prompt", side_effect=["12345", "mypassword"]):
                    result = runner.invoke(app, ["auth", "--phone", "+84912345678"])
                    assert result.exit_code == 0
                    assert "Successfully authenticated as Test User!" in result.stdout
                    assert mock_backend.sign_in.call_count == 2
