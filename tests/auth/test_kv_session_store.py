"""Tests for KvSessionStore — durable per-sub session metadata via mcp-core backend."""

import pytest
from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.auth.in_memory_session_store import SessionInfo
from better_telegram_mcp.auth.kv_session_store import KvSessionStore


def _info(name: str = "s1", phone: str = "+1") -> SessionInfo:
    return SessionInfo(session_name=name, mode="user", phone=phone)


@pytest.fixture(autouse=True)
def _patch_credential_secret(monkeypatch):
    """PerPluginStore's multi-user key derivation requires CREDENTIAL_SECRET."""
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret-32-bytes-padded-here!")


def test_store_and_load_roundtrip():
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)
    store.store("sub-alice", _info("alice_session", "+84901"))
    loaded = store.load("sub-alice")
    assert loaded is not None
    assert loaded.session_name == "alice_session"
    assert loaded.phone == "+84901"


def test_survives_new_instance_same_backend():
    """Recreating KvSessionStore with the same backend restores data (durable)."""
    backend = InMemoryBackend()
    store1 = KvSessionStore(backend=backend)
    store1.store("sub-bob", _info("bob_session", "+1555"))

    store2 = KvSessionStore(backend=backend)
    loaded = store2.load("sub-bob")
    assert loaded is not None
    assert loaded.session_name == "bob_session"


def test_has_any():
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)
    assert store.has_any() is False

    store.store("sub-a", _info("sess_a", "+1"))
    assert store.has_any() is True


def test_load_all_returns_all():
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)
    store.store("sub-a", _info("sess_a", "+1"))
    store.store("sub-b", _info("sess_b", "+2"))

    all_sessions = store.load_all()
    assert set(all_sessions.keys()) == {"sub-a", "sub-b"}
    assert all_sessions["sub-a"].session_name == "sess_a"
    assert all_sessions["sub-b"].session_name == "sess_b"


def test_per_sub_isolation():
    """Each sub's data is encrypted independently; one sub cannot read another's."""
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)
    store.store("sub-x", _info("sess_x", "+100"))
    store.store("sub-y", _info("sess_y", "+200"))

    assert store.load("sub-x").session_name == "sess_x"
    assert store.load("sub-y").session_name == "sess_y"
    assert store.load("sub-z") is None


def test_delete():
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)
    store.store("sub-del", _info("del_session", "+9"))
    assert store.load("sub-del") is not None

    result = store.delete("sub-del")
    assert result is True
    assert store.load("sub-del") is None

    # load_all no longer returns deleted sub
    all_sessions = store.load_all()
    assert "sub-del" not in all_sessions
