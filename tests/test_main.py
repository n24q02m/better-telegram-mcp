"""Tests for __main__.py entry point."""

from __future__ import annotations

from unittest.mock import patch


def test_cli_dispatch():
    """CLI dispatches to cli module."""
    from better_telegram_mcp.__main__ import _cli

    with patch("better_telegram_mcp.cli._cli") as mock_cli_main:
        _cli()
        mock_cli_main.assert_called_once()
