"""Tests for __main__.py entry point."""

from __future__ import annotations

from unittest.mock import patch


def test_cli_runs_app():
    with patch("better_telegram_mcp.cli._cli_entry") as mock_cli:
        from better_telegram_mcp.__main__ import _cli

        _cli()
        mock_cli.assert_called_once()
