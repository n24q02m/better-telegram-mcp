"""Tests for __main__.py entry point."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


def test_cli_runs_server():
    with patch.object(sys, "argv", ["better-telegram-mcp"]):
        mock_server = MagicMock()
        with patch.dict(
            sys.modules,
            {"better_telegram_mcp.server": mock_server},
        ):
            from better_telegram_mcp.__main__ import _cli

            # Typer CLI calls sys.exit(0) on success
            with pytest.raises(SystemExit) as excinfo:
                _cli()

            assert excinfo.value.code == 0
            mock_server.main.assert_called_once()
