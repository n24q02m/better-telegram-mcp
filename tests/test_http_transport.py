"""Tests for HTTP transport mode."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.credential_store import CredentialStore
from better_telegram_mcp.transports.http import setup_credentials


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def settings(data_dir: Path) -> Settings:
    return Settings(data_dir=data_dir)


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


class TestStartHttp:
    def test_start_http_with_stored_credentials(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """start_http should load stored creds and run mcp with streamable-http."""
        store = CredentialStore(data_dir, secret="test")
        store.store({"TELEGRAM_BOT_TOKEN": "stored-token"})

        with (
            patch.dict("os.environ", {"CREDENTIAL_SECRET": "test"}),
            patch("better_telegram_mcp.server.mcp") as mock_mcp,
        ):
            from better_telegram_mcp.transports.http import start_http

            start_http(settings)

        mock_mcp.run.assert_called_once_with(transport="streamable-http")

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
            from better_telegram_mcp.transports.http import start_http

            start_http(settings)

            # Assert inside the context manager before patch.dict restores env
            assert os.environ.get("TELEGRAM_BOT_TOKEN") == "env-token-123"
            assert os.environ.get("TELEGRAM_API_ID") == "99999"


def test_get_current_backend():
    """get_current_backend should return None by default and retrieve set values."""
    from better_telegram_mcp.transports.http import (
        _current_backend,
        get_current_backend,
    )

    # Default is None
    assert get_current_backend() is None

    # After setting, it should return the value
    token = _current_backend.set("test-backend")
    try:
        assert get_current_backend() == "test-backend"
    finally:
        _current_backend.reset(token)

    # Back to None
    assert get_current_backend() is None


def test_is_multi_user_mode():
    """_is_multi_user_mode should return True only when all required env vars are set."""
    from better_telegram_mcp.transports.http import _is_multi_user_mode

    required_vars = {
        "DCR_SERVER_SECRET": "secret",
        "PUBLIC_URL": "https://example.com",
        "TELEGRAM_API_ID": "123",
        "TELEGRAM_API_HASH": "hash",
    }

    # Missing all
    with patch.dict("os.environ", {}, clear=True):
        assert _is_multi_user_mode() is False

    # Set all
    with patch.dict("os.environ", required_vars, clear=True):
        assert _is_multi_user_mode() is True

    # Missing one by one
    for var in required_vars:
        subset = required_vars.copy()
        del subset[var]
        with patch.dict("os.environ", subset, clear=True):
            assert _is_multi_user_mode() is False


def test_start_http_dispatch(settings):
    """start_http should dispatch to either multi or single user mode."""
    from better_telegram_mcp.transports.http import start_http

    with (
        patch(
            "better_telegram_mcp.transports.http._is_multi_user_mode"
        ) as mock_is_multi,
        patch(
            "better_telegram_mcp.transports.http._start_multi_user_http"
        ) as mock_multi,
        patch(
            "better_telegram_mcp.transports.http._start_single_user_http"
        ) as mock_single,
    ):
        # Multi-user path
        mock_is_multi.return_value = True
        start_http(settings)
        mock_multi.assert_called_once_with(settings)
        mock_single.assert_not_called()

        mock_multi.reset_mock()
        mock_single.reset_mock()

        # Single-user path
        mock_is_multi.return_value = False
        start_http(settings)
        mock_single.assert_called_once_with(settings)
        mock_multi.assert_not_called()


def test_start_single_user_http_unconfigured(settings):
    """_start_single_user_http should run setup if unconfigured."""
    from better_telegram_mcp.transports.http import _start_single_user_http

    settings.bot_token = None
    settings.phone = None

    with (
        patch("better_telegram_mcp.transports.http.CredentialStore") as mock_store_cls,
        patch(
            "better_telegram_mcp.transports.http.setup_credentials",
            new_callable=AsyncMock,
        ),
        patch("better_telegram_mcp.server.mcp") as mock_mcp,
        patch("asyncio.run") as mock_asyncio_run,
    ):
        mock_store = mock_store_cls.return_value
        mock_store.load.return_value = None
        creds = {"TELEGRAM_BOT_TOKEN": "setup-token"}
        mock_asyncio_run.return_value = creds

        # Explicitly clear env var if exists
        with patch.dict("os.environ", {}, clear=False):
            if "TELEGRAM_BOT_TOKEN" in os.environ:
                del os.environ["TELEGRAM_BOT_TOKEN"]

            _start_single_user_http(settings)

            assert os.environ.get("TELEGRAM_BOT_TOKEN") == "setup-token"

        mock_asyncio_run.assert_called_once()
        mock_mcp.run.assert_called_once_with(transport="streamable-http")


def test_start_multi_user_http(settings):
    """_start_multi_user_http should initialize and run uvicorn."""
    from better_telegram_mcp.transports.http import _start_multi_user_http

    env = {
        "PORT": "9090",
        "PUBLIC_URL": "https://pub.example.com",
        "DCR_SERVER_SECRET": "dcr-secret",
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "hash123",
        "HOST": "0.0.0.0",
    }

    with (
        patch.dict("os.environ", env, clear=True),
        patch(
            "better_telegram_mcp.transports.http_multi_user.create_app"
        ) as mock_create_app,
        patch("uvicorn.run") as mock_uvicorn_run,
    ):
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        _start_multi_user_http(settings)

        mock_create_app.assert_called_once_with(
            data_dir=settings.data_dir,
            public_url="https://pub.example.com",
            dcr_secret="dcr-secret",
            api_id=12345,
            api_hash="hash123",
        )
        mock_uvicorn_run.assert_called_once_with(
            mock_app, host="0.0.0.0", port=9090, log_level="info"
        )
