"""Tests for __main__.py entry point."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


def test_cli_runs_server():
    with patch.object(sys, "argv", ["better-telegram-mcp"]):
        MagicMock()
        # Mocking the app directly to avoid Typer's SystemExit
        with patch("better_telegram_mcp.cli.app") as mock_app:
            from better_telegram_mcp.__main__ import _cli

            _cli()
            mock_app.assert_called_once()
