"""Tests for __main__.py entry point."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


def test_cli_runs_server():
    with patch.object(sys, "argv", ["better-telegram-mcp"]):
        mock_cli = MagicMock()
        with patch.dict(
            sys.modules,
            {"better_telegram_mcp.cli": mock_cli},
        ):
            from better_telegram_mcp.__main__ import _cli

            _cli()
            # mock_cli.app() is called
            mock_cli.app.assert_called_once()
