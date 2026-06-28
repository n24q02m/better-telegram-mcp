import time
from unittest.mock import patch

import pytest
from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.auth.pending_otp_store import PendingOtpStore

import os

@pytest.fixture(autouse=True)
def set_env():
    os.environ["CREDENTIAL_SECRET"] = "dummysecret"
    yield
    del os.environ["CREDENTIAL_SECRET"]

@pytest.fixture
def backend():
    return InMemoryBackend()

@pytest.fixture
def store(backend):
    return PendingOtpStore(backend=backend)

def test_save_and_load_pending_otp(store):
    sub = "user1"
    bearer = "token1"
    data = {
        "phone": "+1234567890",
        "phone_code_hash": "hash123",
        "session_name": "session_user1",
    }

    store.save_pending_otp(sub, bearer, data)

    loaded = store.load_pending_otp(sub, bearer)
    assert loaded is not None
    assert loaded["phone"] == "+1234567890"
    assert loaded["phone_code_hash"] == "hash123"
    assert loaded["session_name"] == "session_user1"
    assert "created_at" in loaded

def test_load_non_existent(store):
    assert store.load_pending_otp("user1", "token1") is None

def test_delete_pending_otp(store):
    sub = "user1"
    bearer = "token1"
    data = {
        "phone": "+1234567890",
        "phone_code_hash": "hash123",
        "session_name": "session_user1",
    }

    store.save_pending_otp(sub, bearer, data)
    assert store.delete_pending_otp(sub, bearer) is True
    assert store.load_pending_otp(sub, bearer) is None

    assert store.delete_pending_otp(sub, bearer) is False

def test_ttl_expiry_on_load(store):
    sub = "user1"
    bearer = "token1"
    data = {
        "phone": "+1234567890",
        "phone_code_hash": "hash123",
        "session_name": "session_user1",
    }
    store.save_pending_otp(sub, bearer, data)

    with patch("time.time", return_value=time.time() + 400): # +400s is > 300s TTL
        loaded = store.load_pending_otp(sub, bearer)
        assert loaded is None

def test_cleanup_expired(store):
    sub1 = "user1"
    bearer1 = "token1"
    data1 = {"phone": "+1", "phone_code_hash": "h1", "session_name": "s1"}

    sub2 = "user2"
    bearer2 = "token2"
    data2 = {"phone": "+2", "phone_code_hash": "h2", "session_name": "s2", "created_at": time.time() - 400}

    store.save_pending_otp(sub1, bearer1, data1)

    # Manually save expired data
    store2 = store._sub_store(sub2)
    store2.save({bearer2: data2})
    store._save_index([sub1, sub2])

    removed = store.cleanup_expired()
    assert removed == 1

    assert store.load_pending_otp(sub1, bearer1) is not None
    assert store.load_pending_otp(sub2, bearer2) is None

    # Test cleanup empty sub dict
    store2.save({})
    store.cleanup_expired()
    assert sub2 not in store._load_index()

def test_load_index_invalid_data(store):
    store._index_store().save("invalid_data")
    assert store._load_index() == []

def test_load_pending_otp_invalid_data(store):
    store._sub_store("user1").save("invalid_data")
    assert store.load_pending_otp("user1", "token1") is None

    store._sub_store("user1").save({"token1": "invalid_entry"})
    assert store.load_pending_otp("user1", "token1") is None
