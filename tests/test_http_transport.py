"""Tests for HTTP transport mode."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.http import (
    _current_backend,
    _per_request_sub_scope,
    get_current_backend,
    start_http,
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def settings(data_dir: Path) -> Settings:
    return Settings(data_dir=data_dir)


class TestGetCurrentBackend:
    def test_get_current_backend_none(self) -> None:
        """Should return None if context variable is not set."""
        token = _current_backend.set(None)
        try:
            assert get_current_backend() is None
        finally:
            _current_backend.reset(token)

    def test_get_current_backend_set(self) -> None:
        """Should return the backend from context if set."""
        mock_backend = MagicMock()
        token = _current_backend.set(mock_backend)
        try:
            assert get_current_backend() == mock_backend
        finally:
            _current_backend.reset(token)


class TestStartHttp:
    def test_start_http_single_user_uses_local_relay(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """Single-user path dispatches to mcp-core run_http_server so the
        browser paste form + OTP flow render correctly."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "mcp_core.transport.local_server.run_http_server",
                new_callable=AsyncMock,
            ) as mock_run,
        ):
            start_http(settings)

        mock_run.assert_called_once()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["server_name"] == "better-telegram-mcp"
        assert "relay_schema" in kwargs
        assert kwargs["on_credentials_saved"] is not None
        assert kwargs["on_step_submitted"] is not None
        assert kwargs["custom_credential_form_html"] is not None
        # Single-user must NOT pin auth_scope (single shared backend).
        assert kwargs.get("auth_scope") is None

    def test_start_http_multi_user_dispatches_run_http_server(
        self, settings: Settings, tmp_path: Path
    ) -> None:
        """Multi-user path also routes through mcp-core run_http_server but
        with auth_scope=_per_request_sub_scope and a per-sub provider."""
        env = {
            "DCR_SERVER_SECRET": "secret",
            "PUBLIC_URL": "https://mcp.example.com",
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "hash",
            "PORT": "9090",
            "HOST": "0.0.0.0",
        }

        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "mcp_core.transport.local_server.run_http_server",
                new_callable=AsyncMock,
            ) as mock_run,
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.TelegramAuthProvider"
            ) as mock_provider_cls,
        ):
            mock_provider = mock_provider_cls.return_value
            mock_provider.restore_sessions = AsyncMock(return_value=0)
            mock_provider.shutdown = AsyncMock()

            settings_with_api = Settings(
                data_dir=tmp_path / "d",
                api_id=12345,
                api_hash="hash",
            )
            start_http(settings_with_api)

        mock_run.assert_called_once()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["server_name"] == "better-telegram-mcp"
        assert kwargs["host"] == "0.0.0.0"
        assert kwargs["port"] == 9090
        assert kwargs["auth_scope"] is _per_request_sub_scope
        # Per-sub provider should be wired up via lifespan.
        mock_provider.restore_sessions.assert_called_once()
        mock_provider.shutdown.assert_called_once()

    def test_start_http_multi_user_default_port_host(
        self, settings: Settings, tmp_path: Path
    ) -> None:
        """Multi-user uses default port 8080 and binds 0.0.0.0 by default."""
        env = {
            "DCR_SERVER_SECRET": "secret",
            "PUBLIC_URL": "https://mcp.example.com",
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "hash",
        }

        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "mcp_core.transport.local_server.run_http_server",
                new_callable=AsyncMock,
            ) as mock_run,
            patch(
                "better_telegram_mcp.auth.telegram_auth_provider.TelegramAuthProvider"
            ) as mock_provider_cls,
        ):
            mock_provider = mock_provider_cls.return_value
            mock_provider.restore_sessions = AsyncMock(return_value=0)
            mock_provider.shutdown = AsyncMock()

            settings_with_api = Settings(
                data_dir=tmp_path / "d",
                api_id=12345,
                api_hash="hash",
            )
            start_http(settings_with_api)

        kwargs = mock_run.call_args.kwargs
        assert kwargs["port"] == 8080
        assert kwargs["host"] == "0.0.0.0"

    def test_start_http_refuses_public_url_without_multi_user(
        self, settings: Settings
    ) -> None:
        """PUBLIC_URL set without DCR_SERVER_SECRET = refuse start."""
        env = {"PUBLIC_URL": "https://mcp.example.com"}

        with (
            patch.dict("os.environ", env, clear=True),
            pytest.raises(RuntimeError, match="Refusing to start"),
        ):
            start_http(settings)

    def test_start_http_public_url_override_allows_single_user(
        self, settings: Settings
    ) -> None:
        """TELEGRAM_ACCEPT_SHARED_SINGLE_USER=1 opt-in skips the refuse-guard."""
        env = {
            "PUBLIC_URL": "https://mcp.example.com",
            "TELEGRAM_ACCEPT_SHARED_SINGLE_USER": "1",
        }

        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "mcp_core.transport.local_server.run_http_server",
                new_callable=AsyncMock,
            ) as mock_run,
        ):
            start_http(settings)

        mock_run.assert_called_once()


class TestPerRequestSubScope:
    """The auth_scope middleware that pins per-request sub + backend."""

    @pytest.mark.asyncio
    async def test_pins_backend_when_provider_resolves_sub(self) -> None:
        from better_telegram_mcp.credential_state import _current_sub

        mock_backend = MagicMock()
        mock_provider = MagicMock()
        mock_provider.resolve_backend.return_value = mock_backend

        observed: dict[str, object] = {}

        async def _next() -> None:
            observed["sub"] = _current_sub.get()
            observed["backend"] = get_current_backend()

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
            return_value=mock_provider,
        ):
            await _per_request_sub_scope({"sub": "sub-uuid-123"}, _next)

        assert observed["sub"] == "sub-uuid-123"
        assert observed["backend"] is mock_backend
        # Reset cleared the backend (avoid leak across requests).
        assert get_current_backend() is None
        assert _current_sub.get() is None
        mock_provider.resolve_backend.assert_called_once_with("sub-uuid-123")

    @pytest.mark.asyncio
    async def test_skips_backend_when_provider_returns_none(self) -> None:
        """User has not completed setup yet — backend stays unset, tool
        handlers will fail with the standard 'not initialized' error."""
        mock_provider = MagicMock()
        mock_provider.resolve_backend.return_value = None

        async def _next() -> None:
            assert get_current_backend() is None

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.get_global_provider",
            return_value=mock_provider,
        ):
            await _per_request_sub_scope({"sub": "no-creds-yet"}, _next)
