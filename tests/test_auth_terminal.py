"""Tests for auth flow: lifespan pending_auth + _auth_required_response."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestAuthRequiredResponse:
    def test_response_has_both_options(self):
        import better_telegram_mcp.server as srv

        result = json.loads(srv._auth_required_response())
        assert "better-telegram-mcp auth" in result["error"]
        assert "config(action='send_code')" in result["error"]
        assert "config(action='auth'" in result["error"]


class TestLifespanUnauthorized:
    async def test_lifespan_sets_pending_auth(self):
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

        old_pending = srv._pending_auth
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
            ):
                async with _lifespan(mcp):
                    assert srv._pending_auth is True

                mock_user_backend.disconnect.assert_awaited_once()
        finally:
            srv._pending_auth = old_pending

    async def test_lifespan_authorized_no_pending(self):
        import better_telegram_mcp.server as srv
        from better_telegram_mcp.server import _lifespan, mcp

        mock_settings = MagicMock()
        mock_settings.mode = "user"
        mock_settings.api_id = 12345
        mock_settings.api_hash = "testhash"
        mock_settings.phone = "+84912345678"
        mock_settings.password = None

        mock_user_backend = AsyncMock()
        mock_user_backend.is_authorized = AsyncMock(return_value=True)

        old_pending = srv._pending_auth
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
            ):
                async with _lifespan(mcp):
                    assert srv._pending_auth is False
        finally:
            srv._pending_auth = old_pending

    async def test_no_auto_send_code(self):
        """Server should NOT auto-send OTP code on startup."""
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

        old_pending = srv._pending_auth
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
            ):
                async with _lifespan(mcp):
                    # send_code should NOT be called automatically
                    mock_user_backend.send_code.assert_not_awaited()
        finally:
            srv._pending_auth = old_pending
