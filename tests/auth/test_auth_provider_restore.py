"""Tests for TelegramAuthProvider session restore from KvSessionStore."""

import pytest
from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.auth.in_memory_session_store import SessionInfo
from better_telegram_mcp.auth.kv_session_store import KvSessionStore
from better_telegram_mcp.auth.telegram_auth_provider import TelegramAuthProvider


@pytest.fixture(autouse=True)
def _patch_credential_secret(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret-32-bytes-padded-here!")


@pytest.mark.asyncio
async def test_restore_from_kv_store(tmp_path, monkeypatch):
    """restore_sessions() repopulates active_clients from KvSessionStore."""
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "deadbeef")

    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)
    # Pre-populate store with a known sub
    store.store(
        "sub-test-user",
        SessionInfo(session_name="test_session", mode="user", phone="+84901234567"),
    )

    provider = TelegramAuthProvider(
        data_dir=tmp_path,
        api_id=12345,
        api_hash="deadbeef",
        store=store,
    )
    # Before restore: no active clients
    assert provider.active_clients == {}

    await provider.restore_sessions()

    # After restore: sub should be registered in active_clients
    assert "sub-test-user" in provider.active_clients
