"""Tests for PendingOtpStore — durable per-sub pending OTP metadata via mcp-core backend.

The store persists in-flight OTP metadata (phone, phone_code_hash, session_name)
so ``complete_user_auth`` can resume after a container sleep/recreate. These tests
exercise the public API against an InMemoryBackend, including TTL expiry, the
shared index, and ``cleanup_expired`` purging.
"""

import time

import pytest
from mcp_core.storage.backends import InMemoryBackend
from mcp_core.storage.per_plugin_store import PerPluginStore

from better_telegram_mcp.auth.pending_otp_store import (
    _INDEX_LEAF,
    _INDEX_SUB,
    _OTP_TTL,
    _PLUGIN,
    PendingOtpStore,
)


@pytest.fixture(autouse=True)
def _patch_credential_secret(monkeypatch):
    """PerPluginStore's multi-user key derivation requires CREDENTIAL_SECRET."""
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret-32-bytes-padded-here!")


def _data(phone: str = "+84901", *, created_at: float | None = None) -> dict:
    d = {
        "phone": phone,
        "phone_code_hash": "hash-" + phone,
        "session_name": "sess-" + phone,
    }
    if created_at is not None:
        d["created_at"] = created_at
    return d


# ---------------------------------------------------------------------------
# save / load roundtrip
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "bearer-1", _data("+1"))

    loaded = store.load_pending_otp("sub-a", "bearer-1")
    assert loaded is not None
    assert loaded["phone"] == "+1"
    assert loaded["phone_code_hash"] == "hash-+1"
    assert loaded["session_name"] == "sess-+1"
    assert "created_at" in loaded  # auto-populated


def test_save_auto_populates_created_at():
    store = PendingOtpStore(backend=InMemoryBackend())
    before = time.time()
    store.save_pending_otp("sub-a", "bearer-1", _data("+1"))
    loaded = store.load_pending_otp("sub-a", "bearer-1")
    assert loaded is not None
    assert loaded["created_at"] >= before


def test_survives_new_instance_same_backend():
    """A fresh PendingOtpStore on the same backend restores data (durable)."""
    backend = InMemoryBackend()
    PendingOtpStore(backend=backend).save_pending_otp("sub-b", "bearer-x", _data("+2"))

    loaded = PendingOtpStore(backend=backend).load_pending_otp("sub-b", "bearer-x")
    assert loaded is not None
    assert loaded["phone"] == "+2"


def test_multiple_bearers_same_sub():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "bearer-1", _data("+1"))
    store.save_pending_otp("sub-a", "bearer-2", _data("+2"))

    one = store.load_pending_otp("sub-a", "bearer-1")
    two = store.load_pending_otp("sub-a", "bearer-2")
    assert one is not None and one["phone"] == "+1"
    assert two is not None and two["phone"] == "+2"


# ---------------------------------------------------------------------------
# load: not-found / malformed
# ---------------------------------------------------------------------------


def test_load_missing_sub_returns_none():
    store = PendingOtpStore(backend=InMemoryBackend())
    assert store.load_pending_otp("nope", "bearer") is None


def test_load_missing_bearer_returns_none():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "bearer-1", _data("+1"))
    assert store.load_pending_otp("sub-a", "other-bearer") is None


def test_load_non_dict_entry_returns_none():
    """Defensive: a corrupted (non-dict) entry in KV yields None, not a crash."""
    store = PendingOtpStore(backend=InMemoryBackend())
    # Inject a malformed entry through the underlying per-sub store.
    store._sub_store("sub-a").save({"bearer-1": "not-a-dict"})
    assert store.load_pending_otp("sub-a", "bearer-1") is None


# ---------------------------------------------------------------------------
# load: TTL expiry + auto-purge
# ---------------------------------------------------------------------------


def test_load_expired_entry_purged_last_bearer():
    """Expired entry (sole bearer) -> None, store cleared, sub dropped from index."""
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp(
        "sub-a", "bearer-1", _data("+1", created_at=time.time() - _OTP_TTL - 10)
    )

    assert store.load_pending_otp("sub-a", "bearer-1") is None
    # purged: a second load still None and the sub is gone from the index
    assert store.load_pending_otp("sub-a", "bearer-1") is None
    assert "sub-a" not in store._load_index()


def test_load_expired_entry_keeps_other_bearers():
    """Expiring one bearer leaves the other intact (store.save branch)."""
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp(
        "sub-a", "stale", _data("+1", created_at=time.time() - _OTP_TTL - 10)
    )
    store.save_pending_otp("sub-a", "fresh", _data("+2"))

    assert store.load_pending_otp("sub-a", "stale") is None
    assert store.load_pending_otp("sub-a", "fresh") is not None
    assert "sub-a" in store._load_index()


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_existing_returns_true_and_clears_index():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "bearer-1", _data("+1"))

    assert store.delete_pending_otp("sub-a", "bearer-1") is True
    assert store.load_pending_otp("sub-a", "bearer-1") is None
    assert "sub-a" not in store._load_index()


def test_delete_keeps_other_bearers():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "bearer-1", _data("+1"))
    store.save_pending_otp("sub-a", "bearer-2", _data("+2"))

    assert store.delete_pending_otp("sub-a", "bearer-1") is True
    assert store.load_pending_otp("sub-a", "bearer-2") is not None
    assert "sub-a" in store._load_index()


def test_delete_missing_returns_false():
    store = PendingOtpStore(backend=InMemoryBackend())
    assert store.delete_pending_otp("sub-a", "bearer-1") is False
    store.save_pending_otp("sub-a", "bearer-1", _data("+1"))
    assert store.delete_pending_otp("sub-a", "other") is False


# ---------------------------------------------------------------------------
# index management + isolation
# ---------------------------------------------------------------------------


def test_index_tracks_multiple_subs():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "b", _data("+1"))
    store.save_pending_otp("sub-b", "b", _data("+2"))
    assert set(store._load_index()) == {"sub-a", "sub-b"}


def test_save_same_sub_twice_no_duplicate_index_entry():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "b1", _data("+1"))
    store.save_pending_otp("sub-a", "b2", _data("+2"))
    assert store._load_index().count("sub-a") == 1


def test_per_sub_isolation():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-x", "b", _data("+100"))
    store.save_pending_otp("sub-y", "b", _data("+200"))
    x = store.load_pending_otp("sub-x", "b")
    y = store.load_pending_otp("sub-y", "b")
    assert x is not None and x["phone"] == "+100"
    assert y is not None and y["phone"] == "+200"
    assert store.load_pending_otp("sub-z", "b") is None


def test_load_index_empty_when_unset():
    store = PendingOtpStore(backend=InMemoryBackend())
    assert store._load_index() == []


def test_load_index_non_dict_returns_empty():
    """Defensive: a corrupted (non-dict) index payload yields []."""
    store = PendingOtpStore(backend=InMemoryBackend())
    store._index_store().save(["not", "a", "dict"])
    assert store._load_index() == []


# ---------------------------------------------------------------------------
# cleanup_expired
# ---------------------------------------------------------------------------


def test_cleanup_empty_index_returns_zero():
    store = PendingOtpStore(backend=InMemoryBackend())
    assert store.cleanup_expired() == 0


def test_cleanup_removes_only_stale_entries():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp(
        "sub-a", "stale", _data("+1", created_at=time.time() - _OTP_TTL - 10)
    )
    store.save_pending_otp("sub-a", "fresh", _data("+2"))

    assert store.cleanup_expired() == 1
    assert store.load_pending_otp("sub-a", "stale") is None
    assert store.load_pending_otp("sub-a", "fresh") is not None


def test_cleanup_purges_sub_when_all_stale():
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp(
        "sub-a", "b1", _data("+1", created_at=time.time() - _OTP_TTL - 10)
    )

    assert store.cleanup_expired() == 1
    assert "sub-a" not in store._load_index()


def test_cleanup_purges_empty_sub_from_index():
    """A sub in the index whose store holds no entries is dropped (continue branch)."""
    store = PendingOtpStore(backend=InMemoryBackend())
    # Put a sub in the index but leave its per-sub store empty.
    store._save_index(["ghost-sub"])
    assert store.cleanup_expired() == 0
    assert "ghost-sub" not in store._load_index()


def test_cleanup_skips_non_dict_entry():
    """Defensive: a non-dict entry is not counted as stale."""
    store = PendingOtpStore(backend=InMemoryBackend())
    store.save_pending_otp("sub-a", "fresh", _data("+2"))
    # Inject a malformed entry alongside the fresh one.
    sub_store = store._sub_store("sub-a")
    existing = sub_store.load()
    existing["broken"] = "not-a-dict"
    sub_store.save(existing)

    assert store.cleanup_expired() == 0
    assert store.load_pending_otp("sub-a", "fresh") is not None


def test_module_constants():
    """Guard the KV key layout the store contract documents."""
    assert _PLUGIN == "telegram"
    assert _INDEX_SUB == "shared-index"
    assert _INDEX_LEAF == "pending_otp_index"
    assert _OTP_TTL == 300
    # _sub_store / _index_store build PerPluginStore instances
    store = PendingOtpStore(backend=InMemoryBackend())
    assert isinstance(store._sub_store("s"), PerPluginStore)
    assert isinstance(store._index_store(), PerPluginStore)
