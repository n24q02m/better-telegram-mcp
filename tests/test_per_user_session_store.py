"""Tests for PerUserSessionStore (encrypted session storage)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from better_telegram_mcp.auth.per_user_session_store import (
    PerUserSessionStore,
    SessionInfo,
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def store(data_dir: Path) -> PerUserSessionStore:
    return PerUserSessionStore(data_dir, secret="test-secret")


class TestSessionInfo:
    def test_to_dict_roundtrip(self) -> None:
        """SessionInfo should serialize and deserialize correctly."""
        info = SessionInfo(
            session_name="test",
            mode="bot",
            bot_token="123:ABC",
            created_at=1000.0,
        )
        data = info.to_dict()
        restored = SessionInfo.from_dict(data)

        assert restored.session_name == "test"
        assert restored.mode == "bot"
        assert restored.bot_token == "123:ABC"
        assert restored.created_at == 1000.0
        assert restored.api_id is None
        assert restored.phone is None

    def test_user_mode_fields(self) -> None:
        """User mode SessionInfo should preserve all fields."""
        info = SessionInfo(
            session_name="user123",
            mode="user",
            api_id=12345,
            api_hash="abcdef",
            phone="+84912345678",
        )
        data = info.to_dict()
        restored = SessionInfo.from_dict(data)

        assert restored.mode == "user"
        assert restored.api_id == 12345
        assert restored.api_hash == "abcdef"
        assert restored.phone == "+84912345678"
        assert restored.bot_token is None

    def test_created_at_default(self) -> None:
        """created_at should default to current time."""
        info = SessionInfo(session_name="test", mode="bot")
        assert info.created_at > 0


class TestPerUserSessionStore:
    def test_store_load_roundtrip(self, store: PerUserSessionStore) -> None:
        """Session can be stored and loaded back correctly."""
        info = SessionInfo(
            session_name="test",
            mode="bot",
            bot_token="123:ABC",
        )
        store.store("bearer-token-1", info)
        loaded = store.load("bearer-token-1")

        assert loaded is not None
        assert loaded.session_name == "test"
        assert loaded.mode == "bot"
        assert loaded.bot_token == "123:ABC"

    def test_load_returns_none_for_unknown(self, store: PerUserSessionStore) -> None:
        """Loading unknown bearer should return None."""
        assert store.load("nonexistent") is None

    def test_load_returns_none_when_empty(self, store: PerUserSessionStore) -> None:
        """Loading from empty store should return None."""
        assert store.load("any-bearer") is None

    def test_store_multiple_sessions(self, store: PerUserSessionStore) -> None:
        """Multiple sessions can coexist."""
        store.store(
            "bearer-1",
            SessionInfo(session_name="s1", mode="bot", bot_token="t1"),
        )
        store.store(
            "bearer-2",
            SessionInfo(session_name="s2", mode="user", api_id=1, api_hash="h"),
        )

        s1 = store.load("bearer-1")
        s2 = store.load("bearer-2")

        assert s1 is not None
        assert s1.session_name == "s1"
        assert s1.mode == "bot"

        assert s2 is not None
        assert s2.session_name == "s2"
        assert s2.mode == "user"

    def test_load_all(self, store: PerUserSessionStore) -> None:
        """load_all should return all stored sessions."""
        store.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="t1"))
        store.store("b2", SessionInfo(session_name="s2", mode="bot", bot_token="t2"))

        all_sessions = store.load_all()
        assert len(all_sessions) == 2
        assert "b1" in all_sessions
        assert "b2" in all_sessions
        assert all_sessions["b1"].session_name == "s1"
        assert all_sessions["b2"].session_name == "s2"

    def test_load_all_empty(self, store: PerUserSessionStore) -> None:
        """load_all on empty store should return empty dict."""
        assert store.load_all() == {}

    def test_delete_existing(self, store: PerUserSessionStore) -> None:
        """Delete should remove session and return True."""
        store.store(
            "bearer-1",
            SessionInfo(session_name="s1", mode="bot", bot_token="t1"),
        )
        assert store.delete("bearer-1") is True
        assert store.load("bearer-1") is None

    def test_delete_nonexistent(self, store: PerUserSessionStore) -> None:
        """Delete of nonexistent bearer should return False."""
        assert store.delete("nonexistent") is False

    def test_delete_preserves_others(self, store: PerUserSessionStore) -> None:
        """Deleting one session should not affect others."""
        store.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="t1"))
        store.store("b2", SessionInfo(session_name="s2", mode="bot", bot_token="t2"))

        store.delete("b1")

        assert store.load("b1") is None
        loaded = store.load("b2")
        assert loaded is not None
        assert loaded.session_name == "s2"

    def test_overwrite_existing_session(self, store: PerUserSessionStore) -> None:
        """Storing with same bearer should overwrite."""
        store.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="old"))
        store.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="new"))

        loaded = store.load("b1")
        assert loaded is not None
        assert loaded.bot_token == "new"

    def test_encryption_different_secrets(self, data_dir: Path) -> None:
        """Different secrets should not decrypt each other's data."""
        store1 = PerUserSessionStore(data_dir, secret="secret-one")
        store1.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="t1"))

        store2 = PerUserSessionStore(data_dir, secret="secret-two")
        with pytest.raises(InvalidTag):
            store2.load_all()

    def test_persistence_across_instances(self, data_dir: Path) -> None:
        """Sessions should persist across store instances with same secret."""
        store1 = PerUserSessionStore(data_dir, secret="shared-secret")
        store1.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="t1"))

        store2 = PerUserSessionStore(data_dir, secret="shared-secret")
        loaded = store2.load("b1")
        assert loaded is not None
        assert loaded.bot_token == "t1"

    def test_auto_generated_secret_persists(self, data_dir: Path) -> None:
        """Auto-generated secret should be reusable across instances."""
        store1 = PerUserSessionStore(data_dir)
        store1.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="t1"))

        store2 = PerUserSessionStore(data_dir)
        loaded = store2.load("b1")
        assert loaded is not None
        assert loaded.bot_token == "t1"

    def test_data_dir_created_if_missing(self, tmp_path: Path) -> None:
        """Store should create data_dir if it does not exist."""
        nested = tmp_path / "a" / "b" / "c"
        store = PerUserSessionStore(nested, secret="test")
        store.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="t1"))
        assert store.load("b1") is not None

    def test_env_var_secret(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CREDENTIAL_SECRET env var should be used when set."""
        monkeypatch.setenv("CREDENTIAL_SECRET", "env-secret")
        store = PerUserSessionStore(data_dir)
        store.store("b1", SessionInfo(session_name="s1", mode="bot", bot_token="t1"))

        store2 = PerUserSessionStore(data_dir)
        assert store2.load("b1") is not None

        # Different env var should fail
        monkeypatch.setenv("CREDENTIAL_SECRET", "different-env-secret")
        store3 = PerUserSessionStore(data_dir)
        with pytest.raises(InvalidTag):
            store3.load_all()

    def test_legacy_format_migration(self, data_dir: Path) -> None:
        """Sessions stored in legacy format should be loadable and migrated on write."""
        from better_telegram_mcp.auth.per_user_session_store import (
            _LEGACY_SALT,
            _SALT_PREFIX,
        )

        store = PerUserSessionStore(data_dir, secret="test-secret")
        info = SessionInfo(session_name="legacy", mode="bot", bot_token="tok")
        sessions = {"bearer-legacy": info.to_dict()}

        # Manually create legacy formatted data
        key = store._derive_key(_LEGACY_SALT)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        plaintext = json.dumps(sessions).encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        store._path.write_bytes(nonce + ciphertext)

        # Verify it loads correctly
        loaded = store.load("bearer-legacy")
        assert loaded is not None
        assert loaded.session_name == "legacy"
        assert not store._path.read_bytes().startswith(_SALT_PREFIX)

        # Trigger migration on write
        store.store("bearer-new", SessionInfo(session_name="new", mode="bot"))
        data = store._path.read_bytes()
        assert data.startswith(_SALT_PREFIX)
        assert store.load("bearer-legacy") is not None
        assert store.load("bearer-new") is not None
