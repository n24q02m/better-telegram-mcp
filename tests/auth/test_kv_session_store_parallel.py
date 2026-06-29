import pytest
from mcp_core.storage.backends import InMemoryBackend
from better_telegram_mcp.auth.in_memory_session_store import SessionInfo
from better_telegram_mcp.auth.kv_session_store import KvSessionStore

def _info(name: str) -> SessionInfo:
    return SessionInfo(session_name=name, mode="user", phone="+1")

@pytest.fixture(autouse=True)
def _patch_credential_secret(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret-32-bytes-padded-here!")

def test_load_all_many_sessions_parallel():
    """Verify that load_all works correctly with many sessions.
    This test will exercise the parallel implementation once applied.
    """
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)

    num_sessions = 5
    subs = [f"sub-{i}" for i in range(num_sessions)]
    for sub in subs:
        store.store(sub, _info(f"sess-{sub}"))

    all_sessions = store.load_all()
    assert len(all_sessions) == num_sessions
    for sub in subs:
        assert sub in all_sessions
        assert all_sessions[sub].session_name == f"sess-{sub}"

def test_load_all_empty():
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)
    assert store.load_all() == {}

def test_load_all_handles_missing_data():
    """Verify load_all skips subs that exist in index but not in storage."""
    backend = InMemoryBackend()
    store = KvSessionStore(backend=backend)

    store.store("sub-1", _info("sess-1"))
    store.store("sub-2", _info("sess-2"))

    # Manually corrupt the index or delete one sub without updating index
    # (delete sub-2 directly from backend)
    # The key format is "telegram/subs/sub-2/session_meta"
    backend.delete("telegram/subs/sub-2/session_meta")

    all_sessions = store.load_all()
    assert "sub-1" in all_sessions
    assert "sub-2" not in all_sessions
    assert len(all_sessions) == 1
