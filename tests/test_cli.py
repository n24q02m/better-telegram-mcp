"""Tests for __main__.py CLI entry point."""

from __future__ import annotations

from unittest.mock import patch


class TestCliDispatch:
    def test_server_dispatch(self):
        """CLI dispatches to server main."""
        from better_telegram_mcp.__main__ import _cli

        with patch("better_telegram_mcp.server.main") as mock_main:
            _cli()
            mock_main.assert_called_once()
