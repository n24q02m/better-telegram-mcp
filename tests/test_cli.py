"""Tests for CLI implementation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def test_cli_help():
    """Verify CLI help output works and doesn't crash."""
    from typer.testing import CliRunner

    from better_telegram_mcp.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Better Telegram MCP Server CLI" in result.stdout
    assert "auth" in result.stdout


def test_cli_server_start():
    """Verify CLI starts the server by default."""
    from typer.testing import CliRunner

    from better_telegram_mcp.cli import app

    runner = CliRunner()
    with patch("better_telegram_mcp.server.main") as mock_server_main:
        result = runner.invoke(app)
        assert result.exit_code == 0
        mock_server_main.assert_called_once()


def test_cli_server_start_with_transport():
    """Verify CLI respects transport option."""
    from typer.testing import CliRunner

    from better_telegram_mcp.cli import app

    runner = CliRunner()
    with patch("better_telegram_mcp.server.main") as mock_server_main:
        with patch.dict("os.environ", {}):
            result = runner.invoke(app, ["--transport", "http"])
            assert result.exit_code == 0
            import os

            assert os.environ.get("TRANSPORT_MODE") == "http"
            mock_server_main.assert_called_once()


@pytest.mark.asyncio
async def test_run_auth_bot_mode():
    """Verify _run_auth fails in bot mode."""
    import typer

    from better_telegram_mcp.cli import _run_auth

    with patch("better_telegram_mcp.cli.Settings") as mock_settings:
        mock_settings.return_value.mode = "bot"
        with pytest.raises(typer.Exit) as excinfo:
            await _run_auth()
        assert excinfo.value.exit_code == 1


@pytest.mark.asyncio
async def test_run_auth_already_authorized():
    """Verify _run_auth skips if already authorized."""
    from better_telegram_mcp.cli import _run_auth

    with patch("better_telegram_mcp.cli.Settings") as mock_settings:
        mock_settings.return_value.mode = "user"
        with patch(
            "better_telegram_mcp.backends.user_backend.UserBackend"
        ) as mock_backend_cls:
            mock_backend = mock_backend_cls.return_value
            mock_backend.connect = AsyncMock()
            mock_backend.is_authorized = AsyncMock(return_value=True)
            mock_backend.disconnect = AsyncMock()

            with patch("typer.echo") as mock_echo:
                await _run_auth()
                mock_echo.assert_any_call("Already authorized!")


@pytest.mark.asyncio
async def test_run_auth_success():
    """Verify _run_auth success flow."""
    from better_telegram_mcp.cli import _run_auth

    with patch("better_telegram_mcp.cli.Settings") as mock_settings:
        mock_settings.return_value.mode = "user"
        mock_settings.return_value.phone = "+123456789"
        with patch(
            "better_telegram_mcp.backends.user_backend.UserBackend"
        ) as mock_backend_cls:
            mock_backend = mock_backend_cls.return_value
            mock_backend.connect = AsyncMock()
            mock_backend.is_authorized = AsyncMock(return_value=False)
            mock_backend.send_code = AsyncMock()
            mock_backend.sign_in = AsyncMock(return_value={"authenticated_as": "Jules"})
            mock_backend.disconnect = AsyncMock()

            with patch("typer.prompt", return_value="12345"):
                with patch("typer.echo") as mock_echo:
                    await _run_auth()
                    mock_echo.assert_any_call("Successfully authenticated as Jules!")
