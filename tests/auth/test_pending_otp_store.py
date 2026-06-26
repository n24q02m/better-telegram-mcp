import os

import pytest
from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.auth.pending_otp_store import PendingOtpStore


@pytest.fixture(autouse=True)
def set_env():
    os.environ["CREDENTIAL_SECRET"] = (
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    yield
    del os.environ["CREDENTIAL_SECRET"]


@pytest.fixture
def backend():
    return InMemoryBackend()


@pytest.fixture
def store(backend):
    return PendingOtpStore(backend)


def test_store_and_load(store):
    store.save_pending_otp(
        "sub1",
        "bearer1",
        {"phone": "123", "session_name": "sess", "phone_code_hash": "hash"},
    )
    loaded = store.load_pending_otp("sub1", "bearer1")
    assert loaded["phone"] == "123"
    assert loaded["session_name"] == "sess"
    assert loaded["phone_code_hash"] == "hash"
    assert "created_at" in loaded


def test_delete(store):
    store.save_pending_otp(
        "sub1",
        "bearer1",
        {"phone": "123", "session_name": "sess", "phone_code_hash": "hash"},
    )
    store.delete_pending_otp("sub1", "bearer1")
    assert store.load_pending_otp("sub1", "bearer1") is None


def test_cleanup_expired(store, monkeypatch):
    import time

    store.save_pending_otp(
        "sub1",
        "bearer1",
        {"phone": "123", "session_name": "sess", "phone_code_hash": "hash"},
    )

    # Fast forward time beyond TTL
    current_time = time.time()
    monkeypatch.setattr(time, "time", lambda: current_time + 700)
    store.cleanup_expired()

    assert store.load_pending_otp("sub1", "bearer1") is None
