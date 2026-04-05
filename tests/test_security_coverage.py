import os
from pathlib import Path

from better_telegram_mcp.auth.per_user_session_store import (
    PerUserSessionStore,
    SessionInfo,
)
from better_telegram_mcp.transports.credential_store import CredentialStore


def test_credential_store_chmod_unlink_failure(monkeypatch, tmp_path):
    def mock_chmod(*args, **kwargs):
        raise OSError("chmod failed")

    def mock_unlink(*args, **kwargs):
        raise OSError("unlink failed")

    monkeypatch.setattr(os, "chmod", mock_chmod)
    # Also need to patch Path.chmod as it might be used
    monkeypatch.setattr(Path, "chmod", mock_chmod)

    data_dir = tmp_path / "data"
    # Create .salt to trigger unlink in store()
    data_dir.mkdir()
    (data_dir / ".salt").write_bytes(b"salt")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    store = CredentialStore(data_dir)
    store.store({"key": "val"})  # Should hit chmod/unlink except blocks


def test_per_user_session_store_chmod_failure(monkeypatch, tmp_path):
    def mock_chmod(*args, **kwargs):
        raise OSError("chmod failed")

    monkeypatch.setattr(os, "chmod", mock_chmod)
    monkeypatch.setattr(Path, "chmod", mock_chmod)

    data_dir = tmp_path / "data"
    store = PerUserSessionStore(
        data_dir
    )  # Triggers _resolve_or_generate_secret -> chmod

    info = SessionInfo(session_name="test", mode="bot")
    store.store("token", info)  # Triggers _write_all -> chmod
