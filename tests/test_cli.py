"""Tests for better_telegram_mcp.cli CLI."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from better_telegram_mcp.cli import _auth_flow, app

runner = CliRunner()


class TestCliDispatch:
    def test_server_dispatch_default(self):
        """CLI dispatches to server main by default."""
        with patch("better_telegram_mcp.server.main") as mock_main:
            # Clear TRANSPORT_MODE to ensure it's set by callback
            with patch.dict(os.environ, {}, clear=False):
                if "TRANSPORT_MODE" in os.environ:
                    del os.environ["TRANSPORT_MODE"]
                result = runner.invoke(app, [])
                assert result.exit_code == 0
                assert os.environ.get("TRANSPORT_MODE") == "stdio"
                mock_main.assert_called_once()

    def test_server_dispatch_run(self):
        """CLI dispatches to server main via 'run' command."""
        with patch("better_telegram_mcp.server.main") as mock_main:
            result = runner.invoke(app, ["run"])
            assert result.exit_code == 0
            mock_main.assert_called_once()

    def test_server_dispatch_transport_option(self):
        """CLI passes transport option via environment."""
        with patch("better_telegram_mcp.server.main") as mock_main:
            with patch.dict(os.environ, {}, clear=False):
                result = runner.invoke(app, ["--transport", "http"])
                assert result.exit_code == 0
                assert os.environ["TRANSPORT_MODE"] == "http"
                mock_main.assert_called_once()

    @patch("better_telegram_mcp.cli._auth_flow")
    def test_auth_command_calls_flow(self, mock_flow):
        """'auth' command calls _auth_flow."""
        result = runner.invoke(app, ["auth", "--phone", "+123456789"])
        assert result.exit_code == 0
        mock_flow.assert_called_once_with("+123456789")


@pytest.mark.asyncio
class TestAuthFlow:
    @patch("better_telegram_mcp.backends.user_backend.UserBackend")
    @patch("better_telegram_mcp.cli.Settings")
    async def test_auth_flow_already_authorized(
        self, mock_settings_cls, mock_backend_cls
    ):
        mock_settings = MagicMock()
        mock_settings.phone = "+123456789"
        mock_settings_cls.return_value = mock_settings

        mock_backend = AsyncMock()
        mock_backend.is_authorized.return_value = True
        mock_backend_cls.return_value = mock_backend

        with patch("typer.echo") as mock_echo:
            await _auth_flow("+123456789")
            mock_echo.assert_any_call("Already authorized as +123456789")
            mock_backend.connect.assert_called_once()
            mock_backend.disconnect.assert_called_once()

    @patch("better_telegram_mcp.backends.user_backend.UserBackend")
    @patch("better_telegram_mcp.cli.Settings")
    async def test_auth_flow_success(self, mock_settings_cls, mock_backend_cls):
        mock_settings = MagicMock()
        mock_settings.phone = "+123456789"
        mock_settings_cls.return_value = mock_settings

        mock_backend = AsyncMock()
        mock_backend.is_authorized.return_value = False
        mock_backend.sign_in.return_value = {"authenticated_as": "TestUser"}
        mock_backend_cls.return_value = mock_backend

        with patch("typer.prompt", side_effect=["12345"]):
            with patch("typer.echo") as mock_echo:
                await _auth_flow("+123456789")
                mock_echo.assert_any_call("Successfully authenticated as TestUser")
                mock_backend.send_code.assert_called_once_with("+123456789")
                mock_backend.sign_in.assert_called_once_with("+123456789", "12345")

    @patch("better_telegram_mcp.backends.user_backend.UserBackend")
    @patch("better_telegram_mcp.cli.Settings")
    async def test_auth_flow_2fa_success(self, mock_settings_cls, mock_backend_cls):
        mock_settings = MagicMock()
        mock_settings.phone = "+123456789"
        mock_settings_cls.return_value = mock_settings

        mock_backend = AsyncMock()
        mock_backend.is_authorized.return_value = False
        # First sign_in fails with 2FA requirement
        mock_backend.sign_in.side_effect = [
            Exception("2FA password required"),
            {"authenticated_as": "TestUser"},
        ]
        mock_backend_cls.return_value = mock_backend

        with patch("typer.prompt", side_effect=["12345", "password"]):
            with patch("typer.echo") as mock_echo:
                await _auth_flow("+123456789")
                mock_echo.assert_any_call("Successfully authenticated as TestUser")
                assert mock_backend.sign_in.call_count == 2

    @patch("better_telegram_mcp.backends.user_backend.UserBackend")
    @patch("better_telegram_mcp.cli.Settings")
    async def test_auth_flow_failure(self, mock_settings_cls, mock_backend_cls):
        mock_settings = MagicMock()
        mock_settings.phone = "+123456789"
        mock_settings_cls.return_value = mock_settings

        mock_backend = AsyncMock()
        mock_backend.is_authorized.return_value = False
        mock_backend.sign_in.side_effect = Exception("Generic failure")
        mock_backend_cls.return_value = mock_backend

        import typer

        with patch("typer.prompt", side_effect=["12345"]):
            with pytest.raises(typer.Exit) as exc:
                await _auth_flow("+123456789")
            assert exc.value.exit_code == 1
