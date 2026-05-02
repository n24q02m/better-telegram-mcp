"""Tests for HTTP transport mode."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.http import (
    _current_backend,
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
        # Ensure it's clean
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
        """Single-user path should dispatch to mcp-core run_http_server
        so the browser paste form + OTP flow render correctly."""
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

    def test_start_http_multi_user(self, settings: Settings) -> None:
        """start_http should start multi-user server if required env vars are set."""
        env = {
            "DCR_SERVER_SECRET": "secret",
            "PUBLIC_URL": "https://mcp.example.com",
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "hash",
            "PORT": "9090",
            "HOST": "0.0.0.0",
        }

        with (
            patch.dict("os.environ", env),
            patch(
                "better_telegram_mcp.transports.oauth_server.create_app"
            ) as mock_create_app,
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            mock_app = MagicMock()
            mock_create_app.return_value = mock_app

            start_http(settings)

            mock_create_app.assert_called_once_with(
                data_dir=settings.data_dir,
                public_url="https://mcp.example.com",
                master_secret="secret",
            )
            mock_uvicorn_run.assert_called_once_with(
                mock_app, host="0.0.0.0", port=9090, log_level="info"
            )

    def test_start_http_multi_user_default_port_host(self, settings: Settings) -> None:
        """start_http multi-user should use default port/host if not provided."""
        env = {
            "DCR_SERVER_SECRET": "secret",
            "PUBLIC_URL": "https://mcp.example.com",
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "hash",
        }

        with (
            patch.dict("os.environ", env, clear=True),
            patch("better_telegram_mcp.transports.oauth_server.create_app"),
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            start_http(settings)

            # Check arguments of the last uvicorn.run call
            _, kwargs = mock_uvicorn_run.call_args
            assert kwargs["port"] == 8080
            assert kwargs["host"] == "127.0.0.1"

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
