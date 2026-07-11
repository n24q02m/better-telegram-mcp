"""Tests for better_telegram_mcp.cli -- shared mcp_core CLI builder mount.

Bare invocation and any leading-dash argv start the server unchanged;
subcommands (login/logout) run one-shot operator actions. No network or
Telegram calls -- the backends, single-user config store, and api-identity
marker store are mocked; OTP/2FA prompts are driven via patched stdin/getpass.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestServeDispatch:
    """Bare/flag argv route to the server unchanged."""

    def test_bare_invocation_starts_server(self):
        from better_telegram_mcp import cli

        with (
            patch.object(sys, "argv", ["better-telegram-mcp"]),
            patch("better_telegram_mcp.server.main") as mock_server_main,
        ):
            rc = cli.main()

        mock_server_main.assert_called_once()
        assert rc == 0

    def test_http_flag_passes_through(self):
        from better_telegram_mcp import cli

        with (
            patch.object(sys, "argv", ["better-telegram-mcp", "--http"]),
            patch("better_telegram_mcp.server.main") as mock_server_main,
        ):
            rc = cli.main()

        mock_server_main.assert_called_once()
        assert rc == 0


class TestLoginArgs:
    """login requires exactly one of --bot-token / --phone."""

    def test_no_flags_errors(self):
        from better_telegram_mcp import cli

        with patch.object(sys, "argv", ["better-telegram-mcp", "login"]):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 2

    def test_both_flags_errors(self):
        from better_telegram_mcp import cli

        with patch.object(
            sys,
            "argv",
            ["better-telegram-mcp", "login", "--bot-token", "x", "--phone", "+1"],
        ):
            with pytest.raises(SystemExit) as exc:
                cli.main()
        assert exc.value.code == 2


class TestLoginBot:
    """`login --bot-token` validates via BotBackend then persists config."""

    def test_happy_path_persists_and_prints(self, capsys):
        from better_telegram_mcp import cli

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()

        with (
            patch.object(
                sys, "argv", ["better-telegram-mcp", "login", "--bot-token", "123:ABC"]
            ),
            patch(
                "better_telegram_mcp.backends.bot_backend.BotBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.credential_state._write_single_user_config"
            ) as mock_write,
        ):
            rc = cli.main()

        assert rc == 0
        mock_backend.connect.assert_awaited_once()
        mock_backend.disconnect.assert_awaited_once()
        mock_write.assert_called_once_with({"TELEGRAM_BOT_TOKEN": "123:ABC"})
        assert "bot mode" in capsys.readouterr().out

    def test_invalid_token_returns_1_and_does_not_persist(self, capsys):
        from better_telegram_mcp import cli

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock(side_effect=Exception("Invalid bot token"))
        mock_backend.disconnect = AsyncMock()

        with (
            patch.object(
                sys, "argv", ["better-telegram-mcp", "login", "--bot-token", "bad"]
            ),
            patch(
                "better_telegram_mcp.backends.bot_backend.BotBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.credential_state._write_single_user_config"
            ) as mock_write,
        ):
            rc = cli.main()

        assert rc == 1
        mock_write.assert_not_called()
        assert "Login failed" in capsys.readouterr().err


class TestLoginPhone:
    """`login --phone` is interactive tty-only; OTP + optional 2FA."""

    def test_non_tty_returns_1(self, capsys):
        from better_telegram_mcp import cli

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False

        with (
            patch.object(
                sys,
                "argv",
                ["better-telegram-mcp", "login", "--phone", "+84900000000"],
            ),
            patch.object(sys, "stdin", mock_stdin),
        ):
            rc = cli.main()

        assert rc == 1
        assert "interactive terminal" in capsys.readouterr().err

    def test_tty_happy_path_persists_config_and_marker(self, capsys):
        from better_telegram_mcp import cli

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.send_code = AsyncMock()
        mock_backend.sign_in = AsyncMock(return_value={"authenticated_as": "Alice"})
        mock_backend.disconnect = AsyncMock()

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdin.readline.return_value = "12345\n"

        mock_store = MagicMock()

        with (
            patch.object(
                sys,
                "argv",
                ["better-telegram-mcp", "login", "--phone", "+84900000000"],
            ),
            patch.object(sys, "stdin", mock_stdin),
            patch(
                "better_telegram_mcp.backends.user_backend.UserBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.credential_state._write_single_user_config"
            ) as mock_write,
            patch(
                "mcp_core.storage.per_plugin_store.PerPluginStore",
                return_value=mock_store,
            ),
        ):
            rc = cli.main()

        assert rc == 0
        mock_backend.send_code.assert_awaited_once_with("+84900000000")
        mock_backend.sign_in.assert_awaited_once_with("+84900000000", "12345")
        mock_backend.disconnect.assert_awaited_once()
        mock_write.assert_called_once_with({"TELEGRAM_PHONE": "+84900000000"})
        mock_store.save.assert_called_once()
        saved = mock_store.save.call_args[0][0]
        assert "api_id" in saved
        assert "Logged in as Alice" in capsys.readouterr().out

    def test_tty_2fa_path_reissues_signin_with_password(self, capsys):
        from better_telegram_mcp import cli

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.send_code = AsyncMock()
        # First sign_in (no password) raises a 2FA-needed error; second succeeds.
        mock_backend.sign_in = AsyncMock(
            side_effect=[
                Exception("2FA password required"),
                {"authenticated_as": "Bob"},
            ]
        )
        mock_backend.disconnect = AsyncMock()

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdin.readline.return_value = "54321\n"

        mock_store = MagicMock()

        with (
            patch.object(
                sys,
                "argv",
                ["better-telegram-mcp", "login", "--phone", "+84900000000"],
            ),
            patch.object(sys, "stdin", mock_stdin),
            patch("getpass.getpass", return_value="s3cret"),
            patch(
                "better_telegram_mcp.backends.user_backend.UserBackend",
                return_value=mock_backend,
            ),
            patch("better_telegram_mcp.credential_state._write_single_user_config"),
            patch(
                "mcp_core.storage.per_plugin_store.PerPluginStore",
                return_value=mock_store,
            ),
        ):
            rc = cli.main()

        assert rc == 0
        assert mock_backend.sign_in.await_count == 2
        second_call = mock_backend.sign_in.await_args_list[1]
        assert second_call.args == ("+84900000000", "54321")
        assert second_call.kwargs == {"password": "s3cret"}
        assert "Logged in as Bob" in capsys.readouterr().out

    def test_tty_signin_failure_returns_1(self, capsys):
        from better_telegram_mcp import cli

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.send_code = AsyncMock()
        mock_backend.sign_in = AsyncMock(side_effect=Exception("Invalid OTP code"))
        mock_backend.disconnect = AsyncMock()

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdin.readline.return_value = "00000\n"

        with (
            patch.object(
                sys,
                "argv",
                ["better-telegram-mcp", "login", "--phone", "+84900000000"],
            ),
            patch.object(sys, "stdin", mock_stdin),
            patch(
                "better_telegram_mcp.backends.user_backend.UserBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.credential_state._write_single_user_config"
            ) as mock_write,
        ):
            rc = cli.main()

        assert rc == 1
        mock_write.assert_not_called()
        mock_backend.disconnect.assert_awaited_once()
        assert "Login failed" in capsys.readouterr().err


class TestLogout:
    """`logout` revokes + deletes the session, config, and marker; idempotent."""

    def test_with_session_revokes_and_clears(self, tmp_path, capsys):
        from better_telegram_mcp import cli

        session_file = tmp_path / "default.session"
        session_file.write_text("x")

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.log_out = AsyncMock(return_value=True)
        mock_backend.disconnect = AsyncMock()

        mock_store = MagicMock()
        mock_store.load.return_value = {"api_id": "37984984"}

        with (
            patch.object(sys, "argv", ["better-telegram-mcp", "logout"]),
            patch.dict(os.environ, {"TELEGRAM_DATA_DIR": str(tmp_path)}, clear=False),
            patch(
                "better_telegram_mcp.backends.user_backend.UserBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.credential_state._read_single_user_config",
                return_value={"TELEGRAM_PHONE": "+84900000000"},
            ),
            patch(
                "better_telegram_mcp.credential_state._delete_single_user_config"
            ) as mock_del,
            patch(
                "mcp_core.storage.per_plugin_store.PerPluginStore",
                return_value=mock_store,
            ),
        ):
            rc = cli.main()

        assert rc == 0
        assert not session_file.exists()
        mock_backend.log_out.assert_awaited_once()
        mock_del.assert_called_once()
        mock_store.clear.assert_called_once()
        out = capsys.readouterr().out
        assert "Logged out" in out

    def test_revoke_failure_is_best_effort(self, tmp_path, capsys):
        from better_telegram_mcp import cli

        session_file = tmp_path / "default.session"
        session_file.write_text("x")

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.log_out = AsyncMock(side_effect=Exception("network down"))
        mock_backend.disconnect = AsyncMock()

        mock_store = MagicMock()
        mock_store.load.return_value = None

        with (
            patch.object(sys, "argv", ["better-telegram-mcp", "logout"]),
            patch.dict(os.environ, {"TELEGRAM_DATA_DIR": str(tmp_path)}, clear=False),
            patch(
                "better_telegram_mcp.backends.user_backend.UserBackend",
                return_value=mock_backend,
            ),
            patch(
                "better_telegram_mcp.credential_state._read_single_user_config",
                return_value=None,
            ),
            patch("better_telegram_mcp.credential_state._delete_single_user_config"),
            patch(
                "mcp_core.storage.per_plugin_store.PerPluginStore",
                return_value=mock_store,
            ),
        ):
            rc = cli.main()

        # Revoke failed, but the local session file is still deleted (rc 0).
        assert rc == 0
        assert not session_file.exists()
        captured = capsys.readouterr()
        assert "could not revoke" in captured.err
        assert "Logged out" in captured.out

    def test_no_session_nothing_to_log_out(self, tmp_path, capsys):
        from better_telegram_mcp import cli

        mock_store = MagicMock()
        mock_store.load.return_value = None

        with (
            patch.object(sys, "argv", ["better-telegram-mcp", "logout"]),
            patch.dict(os.environ, {"TELEGRAM_DATA_DIR": str(tmp_path)}, clear=False),
            patch(
                "better_telegram_mcp.credential_state._read_single_user_config",
                return_value=None,
            ),
            patch(
                "mcp_core.storage.per_plugin_store.PerPluginStore",
                return_value=mock_store,
            ),
        ):
            rc = cli.main()

        assert rc == 0
        assert "Nothing to log out" in capsys.readouterr().out
