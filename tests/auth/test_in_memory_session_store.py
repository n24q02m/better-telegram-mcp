"""Tests for InMemorySessionStore (TC-NearZK trust class)."""

from __future__ import annotations

from better_telegram_mcp.auth.in_memory_session_store import InMemorySessionStore
from better_telegram_mcp.auth.per_user_session_store import SessionInfo


def _bot_info(token: str = "123:ABC") -> SessionInfo:
    return SessionInfo(session_name="test", mode="bot", bot_token=token)


def _user_info(phone: str = "+1111") -> SessionInfo:
    return SessionInfo(
        session_name="user-sess",
        mode="user",
        api_id=12345,
        api_hash="abcdef",
        phone=phone,
    )


class TestInMemorySessionStoreRoundTrip:
    def test_store_and_load(self) -> None:
        store = InMemorySessionStore()
        info = _bot_info()
        store.store("bearer-a", info)
        loaded = store.load("bearer-a")
        assert loaded is not None
        assert loaded.session_name == "test"
        assert loaded.bot_token == "123:ABC"

    def test_load_returns_none_for_unknown(self) -> None:
        store = InMemorySessionStore()
        assert store.load("nonexistent") is None

    def test_load_returns_none_when_empty(self) -> None:
        store = InMemorySessionStore()
        assert store.load("any-bearer") is None

    def test_overwrite_existing(self) -> None:
        store = InMemorySessionStore()
        store.store("b1", _bot_info("old"))
        store.store("b1", _bot_info("new"))
        loaded = store.load("b1")
        assert loaded is not None
        assert loaded.bot_token == "new"

    def test_returns_copy_not_reference(self) -> None:
        """Mutations to loaded SessionInfo must not affect stored data."""
        store = InMemorySessionStore()
        store.store("b1", _bot_info("original"))
        loaded = store.load("b1")
        assert loaded is not None
        loaded.bot_token = "mutated"
        loaded2 = store.load("b1")
        assert loaded2 is not None
        assert loaded2.bot_token == "original"


class TestInMemorySessionStoreIsolation:
    def test_per_bearer_isolation(self) -> None:
        store = InMemorySessionStore()
        store.store("bearer-a", _bot_info("token-a"))
        store.store("bearer-b", _bot_info("token-b"))
        a = store.load("bearer-a")
        b = store.load("bearer-b")
        assert a is not None and a.bot_token == "token-a"
        assert b is not None and b.bot_token == "token-b"

    def test_sessions_lost_on_new_instance(self) -> None:
        """Simulate restart: new InMemorySessionStore has no prior data."""
        store1 = InMemorySessionStore()
        store1.store("bearer-a", _bot_info())
        assert store1.load("bearer-a") is not None

        store2 = InMemorySessionStore()
        assert store2.load("bearer-a") is None


class TestInMemorySessionStoreDelete:
    def test_delete_existing_returns_true(self) -> None:
        store = InMemorySessionStore()
        store.store("b1", _bot_info())
        assert store.delete("b1") is True
        assert store.load("b1") is None

    def test_delete_nonexistent_returns_false(self) -> None:
        store = InMemorySessionStore()
        assert store.delete("nonexistent") is False

    def test_delete_preserves_others(self) -> None:
        store = InMemorySessionStore()
        store.store("b1", _bot_info("t1"))
        store.store("b2", _bot_info("t2"))
        store.delete("b1")
        assert store.load("b1") is None
        loaded = store.load("b2")
        assert loaded is not None and loaded.bot_token == "t2"


class TestInMemorySessionStoreLoadAll:
    def test_load_all_empty(self) -> None:
        store = InMemorySessionStore()
        assert store.load_all() == {}

    def test_load_all_returns_all(self) -> None:
        store = InMemorySessionStore()
        store.store("b1", _bot_info("t1"))
        store.store("b2", _bot_info("t2"))
        all_sessions = store.load_all()
        assert len(all_sessions) == 2
        assert "b1" in all_sessions
        assert "b2" in all_sessions
        assert all_sessions["b1"].bot_token == "t1"
        assert all_sessions["b2"].bot_token == "t2"

    def test_load_all_returns_copy(self) -> None:
        """Mutations to load_all() result must not affect stored data."""
        store = InMemorySessionStore()
        store.store("b1", _bot_info("original"))
        all_sessions = store.load_all()
        all_sessions["b1"].bot_token = "mutated"
        loaded = store.load("b1")
        assert loaded is not None
        assert loaded.bot_token == "original"
