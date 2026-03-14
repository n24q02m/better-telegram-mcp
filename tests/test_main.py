from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


def test_cli_runs_server():
    with patch.object(sys, "argv", ["better-telegram-mcp"]):
        mock_server = MagicMock()
        with patch.dict(
            sys.modules,
            {"better_telegram_mcp.server": mock_server},
        ):
            from better_telegram_mcp.__main__ import _cli

            _cli()
            mock_server.main.assert_called_once()


def test_cli_runs_auth():
    with patch.object(sys, "argv", ["better-telegram-mcp", "auth"]):
        mock_cli = MagicMock()
        with patch.dict(
            sys.modules,
            {"better_telegram_mcp.cli": mock_cli},
        ):
            # Need to reload to pick up the patched module
            import importlib

            import better_telegram_mcp.__main__ as main_mod

            importlib.reload(main_mod)
            main_mod._cli()
            mock_cli.run_auth.assert_called_once()
