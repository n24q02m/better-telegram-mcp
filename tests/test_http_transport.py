"""Tests for HTTP transport mode."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.credential_store import CredentialStore
from better_telegram_mcp.transports.http import (
    _current_backend,
    _is_multi_user_mode,
    get_current_backend,
    setup_credentials,
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
        """Should return None when ContextVar is not set."""
        assert get_current_backend() is None

    def test_get_current_backend_set(self) -> None:
        """Should return the value set in ContextVar."""
        mock_backend = MagicMock()
        token = _current_backend.set(mock_backend)
        try:
            assert get_current_backend() is mock_backend
        finally:
            _current_backend.reset(token)


class TestSetupCredentials:
    async def test_loads_stored_credentials(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """Should return stored credentials without hitting relay."""
        store = CredentialStore(data_dir, secret="test")
        expected = {"TELEGRAM_BOT_TOKEN": "stored-token"}
        store.store(expected)

        # Patch env so CredentialStore inside setup_credentials uses same secret
        with patch.dict("os.environ", {"CREDENTIAL_SECRET": "test"}):
            result = await setup_credentials(settings)

        assert result == expected

    async def test_triggers_relay_when_no_credentials(self, settings: Settings) -> None:
        """Should call relay when no stored credentials exist."""
        mock_session = MagicMock()
        mock_session.relay_url = "https://relay.example.com/setup/abc"

        expected_creds = {"TELEGRAM_BOT_TOKEN": "relay-token"}

        with (
            patch(
                "better_telegram_mcp.transports.http.create_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ) as mock_create,
            patch(
                "better_telegram_mcp.transports.http.poll_for_result",
                new_callable=AsyncMock,
                return_value=expected_creds,
            ) as mock_poll,
        ):
            result = await setup_credentials(settings)

        assert result == expected_creds
        mock_create.assert_called_once()
        mock_poll.assert_called_once()

    async def test_relay_failure_raises(self, settings: Settings) -> None:
        """Should raise RuntimeError when relay server is unreachable."""
        with patch(
            "better_telegram_mcp.transports.http.create_session",
            new_callable=AsyncMock,
            side_effect=ConnectionError("unreachable"),
        ):
            with pytest.raises(RuntimeError, match="Cannot reach relay server"):
                await setup_credentials(settings)

    async def test_relay_timeout_raises(self, settings: Settings) -> None:
        """Should raise RuntimeError when relay setup times out."""
        mock_session = MagicMock()
        mock_session.relay_url = "https://relay.example.com/setup/abc"

        with (
            patch(
                "better_telegram_mcp.transports.http.create_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch(
                "better_telegram_mcp.transports.http.poll_for_result",
                new_callable=AsyncMock,
                side_effect=RuntimeError("timeout"),
            ),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                await setup_credentials(settings)

    async def test_credentials_stored_after_relay(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """Credentials from relay should be persisted to disk."""
        mock_session = MagicMock()
        mock_session.relay_url = "https://relay.example.com/setup/abc"
        expected_creds = {"TELEGRAM_BOT_TOKEN": "new-token"}

        with (
            patch(
                "better_telegram_mcp.transports.http.create_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch(
                "better_telegram_mcp.transports.http.poll_for_result",
                new_callable=AsyncMock,
                return_value=expected_creds,
            ),
        ):
            await setup_credentials(settings)

        # Verify credentials were persisted
        store = CredentialStore(data_dir)
        assert store.load() == expected_creds


class TestIsMultiUserMode:
    def test_is_multi_user_mode_false_missing_vars(self) -> None:
        """Should return False if any required env var is missing."""
        with patch.dict("os.environ", {}, clear=True):
            assert _is_multi_user_mode() is False

        with patch.dict("os.environ", {"DCR_SERVER_SECRET": "s"}, clear=True):
            assert _is_multi_user_mode() is False

    def test_is_multi_user_mode_true(self) -> None:
        """Should return True if all required env vars are present."""
        env = {
            "DCR_SERVER_SECRET": "secret",
            "PUBLIC_URL": "https://example.com",
            "TELEGRAM_API_ID": "123",
            "TELEGRAM_API_HASH": "hash",
        }
        with patch.dict("os.environ", env, clear=True):
            assert _is_multi_user_mode() is True


class TestStartHttp:
    def test_start_http_dispatches_to_single_user(self, settings: Settings) -> None:
        """Should call _start_single_user_http when not in multi-user mode."""
        with (
            patch(
                "better_telegram_mcp.transports.http._is_multi_user_mode",
                return_value=False,
            ),
            patch(
                "better_telegram_mcp.transports.http._start_single_user_http"
            ) as mock_single,
        ):
            start_http(settings)
            mock_single.assert_called_once_with(settings)

    def test_start_http_dispatches_to_multi_user(self, settings: Settings) -> None:
        """Should call _start_multi_user_http when in multi-user mode."""
        with (
            patch(
                "better_telegram_mcp.transports.http._is_multi_user_mode",
                return_value=True,
            ),
            patch(
                "better_telegram_mcp.transports.http._start_multi_user_http"
            ) as mock_multi,
        ):
            start_http(settings)
            mock_multi.assert_called_once_with(settings)

    def test_start_single_user_http_with_stored_credentials(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """_start_single_user_http should load stored creds and run mcp."""
        store = CredentialStore(data_dir, secret="test")
        store.store({"TELEGRAM_BOT_TOKEN": "stored-token"})

        with (
            patch.dict("os.environ", {"CREDENTIAL_SECRET": "test"}),
            patch("better_telegram_mcp.server.mcp") as mock_mcp,
        ):
            from better_telegram_mcp.transports.http import _start_single_user_http

            _start_single_user_http(settings)

        mock_mcp.run.assert_called_once_with(transport="streamable-http")

    def test_start_single_user_http_triggers_setup(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """_start_single_user_http should trigger setup_credentials if no creds."""
        expected_creds = {"TELEGRAM_BOT_TOKEN": "new-token"}

        with (
            patch.dict("os.environ", {"CREDENTIAL_SECRET": "test"}),
            patch(
                "better_telegram_mcp.transports.http.setup_credentials",
                new_callable=AsyncMock,
                return_value=expected_creds,
            ) as mock_setup,
            patch("better_telegram_mcp.server.mcp") as mock_mcp,
        ):
            from better_telegram_mcp.transports.http import _start_single_user_http

            _start_single_user_http(settings)

            mock_setup.assert_called_once()
            assert os.environ.get("TELEGRAM_BOT_TOKEN") == "new-token"

        mock_mcp.run.assert_called_once_with(transport="streamable-http")

    def test_start_multi_user_http(self, settings: Settings) -> None:
        """_start_multi_user_http should initialize app and run uvicorn."""
        env = {
            "DCR_SERVER_SECRET": "secret",
            "PUBLIC_URL": "https://example.com",
            "TELEGRAM_API_ID": "123",
            "TELEGRAM_API_HASH": "hash",
            "PORT": "9090",
            "HOST": "0.0.0.0",
        }
        mock_app = MagicMock()

        # We must patch where it's imported FROM since it's a relative import
        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "better_telegram_mcp.transports.http_multi_user.create_app",
                return_value=mock_app,
            ) as mock_create_app,
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            from better_telegram_mcp.transports.http import _start_multi_user_http

            _start_multi_user_http(settings)

            mock_create_app.assert_called_once_with(
                data_dir=settings.data_dir,
                public_url="https://example.com",
                dcr_secret="secret",
                api_id=123,
                api_hash="hash",
            )
            mock_uvicorn_run.assert_called_once_with(
                mock_app, host="0.0.0.0", port=9090, log_level="info"
            )
