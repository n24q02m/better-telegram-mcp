"""Tests for better_telegram_mcp.cli CLI."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from better_telegram_mcp.cli import app

runner = CliRunner()


class TestCliDispatch:
    def test_server_dispatch_default(self):
        """CLI dispatches to server main by default."""
        with patch("better_telegram_mcp.server.main") as mock_main:
            result = runner.invoke(app, [])
            assert result.exit_code == 0
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
            with patch.dict("os.environ", {}):
                result = runner.invoke(app, ["--transport", "http"])
                assert result.exit_code == 0
                import os

                assert os.environ["TRANSPORT_MODE"] == "http"
                mock_main.assert_called_once()

    @patch("better_telegram_mcp.cli._auth_flow")
    def test_auth_command_calls_flow(self, mock_flow):
        """'auth' command calls _auth_flow."""
        result = runner.invoke(app, ["auth", "--phone", "+123456789"])
        assert result.exit_code == 0
        mock_flow.assert_called_once_with("+123456789")
