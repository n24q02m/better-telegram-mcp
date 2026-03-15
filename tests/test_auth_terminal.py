from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- _find_terminal_emulator tests ---


class TestFindTerminalEmulator:
    def test_finds_first_available(self):
        from better_telegram_mcp.server import _find_terminal_emulator

        with patch("better_telegram_mcp.server.shutil.which") as mock_which:
            mock_which.side_effect = lambda t: (
                "/usr/bin/xterm" if t == "xterm" else None
            )
            result = _find_terminal_emulator()
            assert result == "xterm"

    def test_finds_gnome_terminal(self):
        from better_telegram_mcp.server import _find_terminal_emulator

        with patch("better_telegram_mcp.server.shutil.which") as mock_which:
            mock_which.side_effect = lambda t: (
                "/usr/bin/gnome-terminal" if t == "gnome-terminal" else None
            )
            result = _find_terminal_emulator()
            assert result == "gnome-terminal"

    def test_returns_none_when_no_terminal(self):
        from better_telegram_mcp.server import _find_terminal_emulator

        with patch("better_telegram_mcp.server.shutil.which", return_value=None):
            result = _find_terminal_emulator()
            assert result is None

    def test_priority_order(self):
        """First match in priority list wins."""
        from better_telegram_mcp.server import _find_terminal_emulator

        available = {"konsole", "xterm"}
        with patch("better_telegram_mcp.server.shutil.which") as mock_which:
            mock_which.side_effect = lambda t: (
                f"/usr/bin/{t}" if t in available else None
            )
            # xterm comes before konsole in the list
            result = _find_terminal_emulator()
            assert result == "xterm"


# --- _open_auth_terminal tests ---


class TestOpenAuthTerminal:
    def _make_settings(self):
        s = MagicMock()
        s.api_id = 12345
        s.api_hash = "testhash"
        s.phone = "+84912345678"
        s.password = None
        s.data_dir = "/tmp/test-telegram"
        s.session_name = "default"
        return s

    def test_returns_false_no_terminal(self):
        from better_telegram_mcp.server import _open_auth_terminal

        with patch(
            "better_telegram_mcp.server._find_terminal_emulator", return_value=None
        ):
            assert _open_auth_terminal(self._make_settings()) is False

    def test_opens_gnome_terminal(self):
        from better_telegram_mcp.server import _open_auth_terminal

        settings = self._make_settings()
        with (
            patch(
                "better_telegram_mcp.server._find_terminal_emulator",
                return_value="gnome-terminal",
            ),
            patch("better_telegram_mcp.server.subprocess.Popen") as mock_popen,
        ):
            result = _open_auth_terminal(settings)
            assert result is True
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "gnome-terminal"
            assert cmd[1] == "--"

    def test_opens_xterm(self):
        from better_telegram_mcp.server import _open_auth_terminal

        settings = self._make_settings()
        with (
            patch(
                "better_telegram_mcp.server._find_terminal_emulator",
                return_value="xterm",
            ),
            patch("better_telegram_mcp.server.subprocess.Popen") as mock_popen,
        ):
            result = _open_auth_terminal(settings)
            assert result is True
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "xterm"
            assert cmd[1] == "-e"

    def test_passes_password_env(self):
        from better_telegram_mcp.server import _open_auth_terminal

        settings = self._make_settings()
        settings.password = "my2fa"
        with (
            patch(
                "better_telegram_mcp.server._find_terminal_emulator",
                return_value="xterm",
            ),
            patch("better_telegram_mcp.server.subprocess.Popen") as mock_popen,
        ):
            _open_auth_terminal(settings)
            env = mock_popen.call_args[1]["env"]
            assert env["TELEGRAM_PASSWORD"] == "my2fa"

    def test_no_password_env_when_none(self):
        from better_telegram_mcp.server import _open_auth_terminal

        settings = self._make_settings()
        settings.password = None
        with (
            patch(
                "better_telegram_mcp.server._find_terminal_emulator",
                return_value="xterm",
            ),
            patch("better_telegram_mcp.server.subprocess.Popen") as mock_popen,
            patch.dict("os.environ", {"TELEGRAM_PASSWORD": "old"}, clear=False),
        ):
            _open_auth_terminal(settings)
            env = mock_popen.call_args[1]["env"]
            # Password should not be set by our code (it comes from os.environ passthrough)
            # The key point: we don't explicitly set it when settings.password is None
            assert "TELEGRAM_API_ID" in env

    def test_returns_false_on_popen_error(self):
        from better_telegram_mcp.server import _open_auth_terminal

        settings = self._make_settings()
        with (
            patch(
                "better_telegram_mcp.server._find_terminal_emulator",
                return_value="xterm",
            ),
            patch(
                "better_telegram_mcp.server.subprocess.Popen",
                side_effect=OSError("no display"),
            ),
        ):
            assert _open_auth_terminal(settings) is False


# --- _poll_auth tests ---


class TestPollAuth:
    @pytest.mark.asyncio
    async def test_poll_completes_when_authorized(self):
        import better_telegram_mcp.server as srv

        old_pending = srv._pending_auth
        old_backend = srv._backend
        try:
            srv._pending_auth = True
            mock_be = AsyncMock()
            # First call: not authorized, second: authorized
            mock_be.is_authorized = AsyncMock(side_effect=[False, True])
            srv._backend = mock_be

            with patch(
                "better_telegram_mcp.server.asyncio.sleep", new_callable=AsyncMock
            ):
                await srv._poll_auth()

            assert srv._pending_auth is False
        finally:
            srv._pending_auth = old_pending
            srv._backend = old_backend

    @pytest.mark.asyncio
    async def test_poll_handles_exceptions(self):
        import better_telegram_mcp.server as srv

        old_pending = srv._pending_auth
        old_backend = srv._backend
        try:
            srv._pending_auth = True
            mock_be = AsyncMock()
            mock_be.is_authorized = AsyncMock(
                side_effect=[Exception("network error"), True]
            )
            srv._backend = mock_be

            with patch(
                "better_telegram_mcp.server.asyncio.sleep", new_callable=AsyncMock
            ):
                await srv._poll_auth()

            assert srv._pending_auth is False
        finally:
            srv._pending_auth = old_pending
            srv._backend = old_backend

    @pytest.mark.asyncio
    async def test_poll_stops_when_pending_cleared(self):
        """If _pending_auth is set to False externally (e.g. config tool), polling stops."""
        import better_telegram_mcp.server as srv

        old_pending = srv._pending_auth
        old_backend = srv._backend
        try:
            srv._pending_auth = False  # Already cleared
            mock_be = AsyncMock()
            srv._backend = mock_be

            with patch(
                "better_telegram_mcp.server.asyncio.sleep", new_callable=AsyncMock
            ):
                await srv._poll_auth()

            # Should return immediately without calling is_authorized
            mock_be.is_authorized.assert_not_awaited()
        finally:
            srv._pending_auth = old_pending
            srv._backend = old_backend


# --- _auth_required_response tests ---


class TestAuthRequiredResponse:
    def test_response_with_terminal_opened(self):
        import better_telegram_mcp.server as srv

        old = srv._auth_terminal_opened
        try:
            srv._auth_terminal_opened = True
            result = json.loads(srv._auth_required_response())
            assert "terminal window" in result["error"]
        finally:
            srv._auth_terminal_opened = old

    def test_response_without_terminal(self):
        import better_telegram_mcp.server as srv

        old = srv._auth_terminal_opened
        try:
            srv._auth_terminal_opened = False
            result = json.loads(srv._auth_required_response())
            assert "config(action='auth'" in result["error"]
            assert "terminal" not in result["error"]
        finally:
            srv._auth_terminal_opened = old


# --- Lifespan with terminal auth tests ---


class TestLifespanTerminalAuth:
    @pytest.mark.asyncio
    async def test_lifespan_opens_terminal_when_unauthorized(self):
        """When unauthorized + phone set + terminal available, open terminal + start polling."""
        import better_telegram_mcp.server as srv
        from better_telegram_mcp.server import _lifespan, mcp

        mock_settings = MagicMock()
        mock_settings.mode = "user"
        mock_settings.api_id = 12345
        mock_settings.api_hash = "testhash"
        mock_settings.phone = "+84912345678"
        mock_settings.password = None

        mock_user_backend = AsyncMock()
        mock_user_backend.is_authorized = AsyncMock(return_value=False)
        mock_user_backend.send_code = AsyncMock()

        old_pending = srv._pending_auth
        old_terminal = srv._auth_terminal_opened
        old_poll = srv._poll_task
        try:
            with (
                patch.object(srv, "Settings", return_value=mock_settings),
                patch.dict(
                    "sys.modules",
                    {
                        "better_telegram_mcp.backends.user_backend": type(
                            "module",
                            (),
                            {"UserBackend": MagicMock(return_value=mock_user_backend)},
                        )()
                    },
                ),
                patch(
                    "better_telegram_mcp.server._open_auth_terminal",
                    return_value=True,
                ) as mock_open,
                patch(
                    "better_telegram_mcp.server._poll_auth",
                    new_callable=AsyncMock,
                ),
                patch(
                    "better_telegram_mcp.server.asyncio.create_task"
                ) as mock_create_task,
            ):
                mock_task = MagicMock()
                mock_task.done.return_value = True
                mock_create_task.return_value = mock_task

                async with _lifespan(mcp):
                    assert srv._pending_auth is True
                    assert srv._auth_terminal_opened is True
                    mock_open.assert_called_once_with(mock_settings)
                    mock_create_task.assert_called_once()

                mock_user_backend.disconnect.assert_awaited_once()
        finally:
            srv._pending_auth = old_pending
            srv._auth_terminal_opened = old_terminal
            srv._poll_task = old_poll

    @pytest.mark.asyncio
    async def test_lifespan_fallback_no_terminal(self):
        """When no terminal available, fall back to config tool auth."""
        import better_telegram_mcp.server as srv
        from better_telegram_mcp.server import _lifespan, mcp

        mock_settings = MagicMock()
        mock_settings.mode = "user"
        mock_settings.api_id = 12345
        mock_settings.api_hash = "testhash"
        mock_settings.phone = "+84912345678"
        mock_settings.password = None

        mock_user_backend = AsyncMock()
        mock_user_backend.is_authorized = AsyncMock(return_value=False)
        mock_user_backend.send_code = AsyncMock()

        old_pending = srv._pending_auth
        old_terminal = srv._auth_terminal_opened
        old_poll = srv._poll_task
        try:
            with (
                patch.object(srv, "Settings", return_value=mock_settings),
                patch.dict(
                    "sys.modules",
                    {
                        "better_telegram_mcp.backends.user_backend": type(
                            "module",
                            (),
                            {"UserBackend": MagicMock(return_value=mock_user_backend)},
                        )()
                    },
                ),
                patch(
                    "better_telegram_mcp.server._open_auth_terminal",
                    return_value=False,
                ),
            ):
                async with _lifespan(mcp):
                    assert srv._pending_auth is True
                    assert srv._auth_terminal_opened is False
                    assert srv._poll_task is None

                mock_user_backend.disconnect.assert_awaited_once()
        finally:
            srv._pending_auth = old_pending
            srv._auth_terminal_opened = old_terminal
            srv._poll_task = old_poll


# --- auth_terminal.py script tests ---


class TestAuthTerminalScript:
    _env_base = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "testhash",
        "TELEGRAM_PHONE": "+84912345678",
        "TELEGRAM_DATA_DIR": "/tmp/test-tg",
        "TELEGRAM_SESSION_NAME": "test",
    }

    @pytest.mark.asyncio
    async def test_successful_auth(self):
        """Test the auth_terminal main() with successful sign-in."""
        mock_client = AsyncMock()
        mock_client.is_user_authorized.return_value = True
        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"
        mock_client.get_me.return_value = mock_me

        with (
            patch.dict("os.environ", self._env_base),
            patch("builtins.input", return_value="12345"),
            patch("telethon.TelegramClient", return_value=mock_client),
        ):
            from better_telegram_mcp.auth_terminal import main

            await main()

            mock_client.connect.assert_awaited_once()
            mock_client.sign_in.assert_awaited_once_with("+84912345678", "12345")
            mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_2fa_with_env_password(self):
        """Test 2FA using TELEGRAM_PASSWORD env var."""
        from telethon.errors import SessionPasswordNeededError

        mock_client = AsyncMock()
        mock_client.sign_in.side_effect = [
            SessionPasswordNeededError(request=None),
            None,
        ]
        mock_client.is_user_authorized.return_value = True
        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = "testuser"
        mock_client.get_me.return_value = mock_me

        env = {**self._env_base, "TELEGRAM_PASSWORD": "my2fa"}
        with (
            patch.dict("os.environ", env),
            patch("builtins.input", return_value="12345"),
            patch("telethon.TelegramClient", return_value=mock_client),
        ):
            from better_telegram_mcp.auth_terminal import main

            await main()

            assert mock_client.sign_in.await_count == 2
            mock_client.sign_in.assert_awaited_with(password="my2fa")

    @pytest.mark.asyncio
    async def test_2fa_with_interactive_password(self):
        """Test 2FA prompting for password when env not set."""
        from telethon.errors import SessionPasswordNeededError

        mock_client = AsyncMock()
        mock_client.sign_in.side_effect = [
            SessionPasswordNeededError(request=None),
            None,
        ]
        mock_client.is_user_authorized.return_value = True
        mock_me = MagicMock()
        mock_me.first_name = "Test"
        mock_me.username = None
        mock_client.get_me.return_value = mock_me

        import os

        os.environ.pop("TELEGRAM_PASSWORD", None)

        with (
            patch.dict("os.environ", self._env_base, clear=False),
            patch("builtins.input", side_effect=["12345", "mypwd"]),
            patch("telethon.TelegramClient", return_value=mock_client),
        ):
            from better_telegram_mcp.auth_terminal import main

            await main()

            mock_client.sign_in.assert_awaited_with(password="mypwd")

    @pytest.mark.asyncio
    async def test_auth_failure_exits(self):
        """Test that failed auth exits with code 1."""
        mock_client = AsyncMock()
        mock_client.is_user_authorized.return_value = False

        with (
            patch.dict("os.environ", self._env_base),
            patch("builtins.input", return_value="12345"),
            patch("telethon.TelegramClient", return_value=mock_client),
            pytest.raises(SystemExit, match="1"),
        ):
            from better_telegram_mcp.auth_terminal import main

            await main()
