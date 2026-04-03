"""Tests for HTTP transport mode."""

from __future__ import annotations

import asyncio
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
        await store.store(expected)

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
            ),
            patch(
                "better_telegram_mcp.transports.http.poll_for_result",
                new_callable=AsyncMock,
                return_value=expected_creds,
            ),
            patch("better_telegram_mcp.transports.http.CredentialStore") as MockStore,
        ):
            mock_store = MockStore.return_value
            mock_store.load = AsyncMock(return_value=None)
            mock_store.store = AsyncMock()

            result = await setup_credentials(settings)

            assert result == expected_creds
            mock_store.store.assert_called_once_with(expected_creds)

    async def test_credentials_stored_after_relay(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """Credentials from relay should be persisted to store."""
        expected_creds = {"TELEGRAM_BOT_TOKEN": "relay-token"}
        mock_session = MagicMock()

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
            patch.dict("os.environ", {"CREDENTIAL_SECRET": "test"}),
        ):
            await setup_credentials(settings)

        # Verify it was written to disk
        store = CredentialStore(data_dir, secret="test")
        assert await store.load() == expected_creds

    async def test_setup_credentials_timeout_error(self, settings: Settings) -> None:
        """Should raise RuntimeError if polling fails."""
        mock_session = MagicMock()
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
            patch("better_telegram_mcp.transports.http.CredentialStore") as MockStore,
        ):
            mock_store = MockStore.return_value
            mock_store.load = AsyncMock(return_value=None)

            with pytest.raises(RuntimeError, match="timed out"):
                await setup_credentials(settings)

    async def test_setup_credentials_relay_error(self, settings: Settings) -> None:
        """Should raise RuntimeError if relay is unreachable."""
        with (
            patch(
                "better_telegram_mcp.transports.http.create_session",
                new_callable=AsyncMock,
                side_effect=Exception("network error"),
            ),
            patch("better_telegram_mcp.transports.http.CredentialStore") as MockStore,
        ):
            mock_store = MockStore.return_value
            mock_store.load = AsyncMock(return_value=None)

            with pytest.raises(RuntimeError, match="Cannot reach relay"):
                await setup_credentials(settings)


class TestStartHttp:
    def test_start_http_with_stored_credentials(
        self, settings: Settings, data_dir: Path
    ) -> None:
        """start_http should load stored creds and run mcp with streamable-http."""
        store = CredentialStore(data_dir, secret="test")
        asyncio.run(store.store({"TELEGRAM_BOT_TOKEN": "stored-token"}))

        with (
            patch.dict("os.environ", {"CREDENTIAL_SECRET": "test"}),
            patch("better_telegram_mcp.server.mcp") as mock_mcp,
        ):
            from better_telegram_mcp.transports.http import start_http

            start_http(settings)

            mock_mcp.run.assert_called_once_with(transport="streamable-http")
            # Verify env was updated
            import os

            assert os.environ["TELEGRAM_BOT_TOKEN"] == "stored-token"

    def test_start_http_sets_env_vars(self, settings: Settings, data_dir: Path) -> None:
        """start_http should set TELEGRAM_ env vars from stored credentials."""
        import os

        store = CredentialStore(data_dir, secret="test")
        creds = {
            "TELEGRAM_BOT_TOKEN": "env-token-123",
            "TELEGRAM_API_ID": "99999",
        }
        asyncio.run(store.store(creds))

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

            assert os.environ["TELEGRAM_BOT_TOKEN"] == "env-token-123"
            assert os.environ["TELEGRAM_API_ID"] == "99999"
