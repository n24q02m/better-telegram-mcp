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
        # Use same secret as it might be using default
        assert store.load() == expected_creds


class TestStartHttp:
    def test_start_http_single_user_with_stored_credentials(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """start_http should load stored creds and run mcp with streamable-http."""
        store = CredentialStore(data_dir, secret="test")
        store.store({"TELEGRAM_BOT_TOKEN": "stored-token"})

        with (
            patch.dict("os.environ", {"CREDENTIAL_SECRET": "test"}),
            patch("better_telegram_mcp.server.mcp") as mock_mcp,
        ):
            start_http(settings)

        mock_mcp.run.assert_called_once_with(transport="streamable-http")

    def test_start_http_single_user_trigger_setup(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """start_http should trigger setup if no creds found in store/env."""
        expected_creds = {"TELEGRAM_BOT_TOKEN": "setup-token"}

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "better_telegram_mcp.transports.http.setup_credentials",
                new_callable=AsyncMock,
                return_value=expected_creds,
            ),
            patch("better_telegram_mcp.server.mcp") as mock_mcp,
        ):
            # Ensure settings not configured
            with patch.object(Settings, "is_configured", False):
                start_http(settings)
                assert os.environ["TELEGRAM_BOT_TOKEN"] == "setup-token"

        mock_mcp.run.assert_called_once_with(transport="streamable-http")

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

    def test_start_http_sets_env_vars(self, settings: Settings, data_dir: Path) -> None:
        """start_http should set TELEGRAM_ env vars from stored credentials."""
        store = CredentialStore(data_dir, secret="test")
        creds = {
            "TELEGRAM_BOT_TOKEN": "env-token-123",
            "TELEGRAM_API_ID": "99999",
        }
        store.store(creds)

        with (
            patch.dict(
                "os.environ",
                {"CREDENTIAL_SECRET": "test"},
                clear=False,
            ),
            patch("better_telegram_mcp.server.mcp"),
        ):
            start_http(settings)

            # Assert inside the context manager before patch.dict restores env
            assert os.environ.get("TELEGRAM_BOT_TOKEN") == "env-token-123"
            assert os.environ.get("TELEGRAM_API_ID") == "99999"
