"""Tests for PerUserSessionStore in-memory caching."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

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


def test_cache_avoids_repeated_disk_reads(data_dir: Path) -> None:
    """Verifies that multiple loads only result in one disk read and decryption."""
    # Setup data on disk using one instance
    store1 = PerUserSessionStore(data_dir, secret="test-secret")
    info = SessionInfo(session_name="test", mode="bot", bot_token="token")
    store1.store("bearer-1", info)

    # Use a fresh instance with empty cache
    store2 = PerUserSessionStore(data_dir, secret="test-secret")

    # First load should read from disk
    with patch.object(Path, "read_bytes", autospec=True) as mock_read:
        # We need to return valid encrypted data for decrypt not to fail
        # Or we can patch _decrypt directly which is easier to test caching logic
        with patch.object(store2, "_decrypt") as mock_decrypt:
            mock_read.return_value = b"encrypted"
            mock_decrypt.return_value = json.dumps(
                {"bearer-1": info.to_dict()}
            ).encode()

            s1 = store2.load("bearer-1")
            assert s1 is not None
            assert mock_read.call_count == 1
            assert mock_decrypt.call_count == 1

            # Second load should use cache
            s2 = store2.load("bearer-1")
            assert s2 is not None
            assert mock_read.call_count == 1
            assert mock_decrypt.call_count == 1


def test_cache_updated_on_store(store: PerUserSessionStore) -> None:
    """Verifies that store() updates the cache."""
    info = SessionInfo(session_name="test", mode="bot", bot_token="token")

    # Store should populate cache
    store.store("bearer-1", info)

    with patch.object(Path, "read_bytes") as mock_read:
        s1 = store.load("bearer-1")
        assert s1 is not None
        mock_read.assert_not_called()


def test_cache_updated_on_delete(store: PerUserSessionStore) -> None:
    """Verifies that delete() updates the cache."""
    info = SessionInfo(session_name="test", mode="bot", bot_token="token")
    store.store("bearer-1", info)

    # Pre-populate cache (already done by store, but let's be explicit)
    store.load("bearer-1")

    store.delete("bearer-1")

    with patch.object(Path, "read_bytes") as mock_read:
        assert store.load("bearer-1") is None
        mock_read.assert_not_called()


def test_read_all_returns_copy(store: PerUserSessionStore) -> None:
    """Verifies that _read_all returns a copy to prevent accidental cache mutation."""
    info = SessionInfo(session_name="test", mode="bot", bot_token="token")
    store.store("bearer-1", info)

    sessions = store._read_all()
    sessions["mutated"] = {"some": "data"}

    # The cache should not be mutated
    sessions_again = store._read_all()
    assert "mutated" not in sessions_again
