"""check_saved_sessions queries the backend in CF mode instead of FS glob."""

from __future__ import annotations

from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.relay_setup import check_saved_sessions


def test_cf_mode_true_when_index_has_subs(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "k")
    monkeypatch.setenv("MCP_STORAGE_BACKEND", "cf-kv")
    mem = InMemoryBackend()
    from better_telegram_mcp.auth.in_memory_session_store import SessionInfo
    from better_telegram_mcp.auth.kv_session_store import KvSessionStore

    KvSessionStore(backend=mem).store(
        "sub-a", SessionInfo(session_name="s", mode="user", phone="+1")
    )
    assert check_saved_sessions(backend=mem) is True


def test_cf_mode_false_when_empty(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "k")
    monkeypatch.setenv("MCP_STORAGE_BACKEND", "cf-kv")
    assert check_saved_sessions(backend=InMemoryBackend()) is False


def test_local_mode_globs_fs(monkeypatch, tmp_path):
    monkeypatch.delenv("MCP_STORAGE_BACKEND", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    data_dir = tmp_path / ".better-telegram-mcp"
    data_dir.mkdir()
    assert check_saved_sessions() is False
    (data_dir / "default.session").write_text("")
    assert check_saved_sessions() is True
