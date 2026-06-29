"""Tests for TelegramAuthProvider session restore from KvSessionStore."""

from unittest.mock import AsyncMock

import pytest
from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.auth.in_memory_session_store import SessionInfo
from better_telegram_mcp.auth.kv_session_store import KvSessionStore
from better_telegram_mcp.auth.pending_otp_store import PendingOtpStore
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


@pytest.mark.asyncio
async def test_complete_user_auth_restores_pending_otp_from_kv(tmp_path, monkeypatch):
    """complete_user_auth recovers pending OTP metadata from KV after a restart.

    Simulates a container sleep/recreate: the RAM ``_pending_otps`` dict is empty,
    but the metadata persists in the PendingOtpStore (CF KV in prod). The provider
    must reload it, recreate a backend, sign in, and consume the KV entry.
    """
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "deadbeef")

    backend = InMemoryBackend()
    pending_store = PendingOtpStore(backend=backend)
    bearer = "bearer-restart-sub"
    # complete_user_auth keys the pending store by sub == bearer.
    pending_store.save_pending_otp(
        bearer,
        bearer,
        {
            "phone": "+84901234567",
            "phone_code_hash": "hash-abc",
            "session_name": "restored_session",
        },
    )

    provider = TelegramAuthProvider(
        data_dir=tmp_path,
        api_id=12345,
        api_hash="deadbeef",
        backend=backend,
        store=KvSessionStore(backend=backend),
        pending_store=pending_store,
    )
    # Post-restart: nothing in RAM.
    assert provider._pending_otps == {}

    fake_backend = AsyncMock()
    fake_backend.sign_in = AsyncMock(return_value={"id": 42, "username": "restored"})

    async def _fake_init(phone, session_name):
        assert phone == "+84901234567"
        assert session_name == "restored_session"
        return fake_backend

    monkeypatch.setattr(provider, "_init_user_backend", _fake_init)

    result = await provider.complete_user_auth(bearer, "55555")

    assert result == {"id": 42, "username": "restored"}
    fake_backend.sign_in.assert_awaited_once()
    # Consumed from both RAM and KV; active client registered.
    assert bearer not in provider._pending_otps
    assert pending_store.load_pending_otp(bearer, bearer) is None
    assert bearer in provider.active_clients
