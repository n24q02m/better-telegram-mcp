"""Tests for auth flow: lifespan pending_auth + _auth_required_response."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestAuthRequiredResponse:
    def test_response_with_auth_url(self):
        import better_telegram_mcp.server as srv

        old = srv._auth_url
        try:
            srv._auth_url = "http://127.0.0.1:12345"
            result = json.loads(srv._auth_required_response())
            assert "127.0.0.1:12345" in result["error"]
            assert "browser" in result["error"].lower()
        finally:
            srv._auth_url = old

    def test_response_without_auth_url(self):
        import better_telegram_mcp.server as srv

        old = srv._auth_url
        try:
            srv._auth_url = None
            result = json.loads(srv._auth_required_response())
            assert "TELEGRAM_PHONE" in result["error"]
        finally:
            srv._auth_url = old


class TestLifespanUnauthorized:
    async def test_lifespan_sets_pending_auth(self):
        import better_telegram_mcp.server as srv
        from better_telegram_mcp.server import _lifespan, mcp

        mock_settings = MagicMock()
        mock_settings.mode = "user"
        mock_settings.api_id = 12345
        mock_settings.api_hash = "testhash"
        mock_settings.phone = "+84912345678"
        # password removed from settings — entered via web UI only

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
        # password removed from settings — entered via web UI only

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
        # password removed from settings — entered via web UI only

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
