"""Tests for CLI implementation using Typer."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from better_telegram_mcp.cli import app

runner = CliRunner()


def test_cli_run_stdio():
    """Test 'run' command with default (stdio) transport."""
    with patch("better_telegram_mcp.server.mcp.run") as mock_run:
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(transport="stdio")


def test_cli_run_http():
    """Test 'run' command with HTTP transport."""
    with patch("better_telegram_mcp.transports.http.start_http") as mock_start_http:
        result = runner.invoke(app, ["run", "--transport", "http"])
        assert result.exit_code == 0
        mock_start_http.assert_called_once()


def test_cli_default_run():
    """Test default invocation runs the server."""
    with patch("better_telegram_mcp.server.mcp.run") as mock_run:
        # Typer's invoke doesn't trigger the callback logic in the same way as real CLI
        # if no command is provided, but we can test the main callback directly if needed.
        # Actually, CliRunner.invoke(app, []) SHOULD trigger main_callback.
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(transport="stdio")


@patch("better_telegram_mcp.cli._auth_async")
def test_cli_auth(mock_auth_async):
    """Test 'auth' command dispatches to async handler."""
    result = runner.invoke(app, ["auth", "--phone", "+1234567890"])
    assert result.exit_code == 0
    mock_auth_async.assert_called_once_with("+1234567890")


@patch("better_telegram_mcp.cli._auth_relay_async")
def test_cli_auth_relay(mock_auth_relay_async):
    """Test 'auth-relay' command dispatches to async handler."""
    result = runner.invoke(app, ["auth-relay"])
    assert result.exit_code == 0
    mock_auth_relay_async.assert_called_once()
