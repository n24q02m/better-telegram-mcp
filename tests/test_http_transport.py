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
        assert await store.load() == expected_creds


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

            # Assert inside the context manager before patch.dict restores env
            assert os.environ.get("TELEGRAM_BOT_TOKEN") == "env-token-123"
            assert os.environ.get("TELEGRAM_API_ID") == "99999"
