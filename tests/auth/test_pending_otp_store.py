from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from better_telegram_mcp.auth.pending_otp_store import PendingOtpStore


@pytest.fixture(autouse=True)
def _patch_credential_secret(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret-32-bytes-padded-here!")


class TestPendingOtpStore:
    def test_save_and_load_pending_otp(self):
        mock_backend = MagicMock()
        store = PendingOtpStore(backend=mock_backend)

        # We'll use a mocked PerPluginStore.load/save
        store._sub_store = MagicMock()
        mock_sub_store = store._sub_store.return_value
        mock_sub_store.load.return_value = {}

        store._index_store = MagicMock()
        mock_index_store = store._index_store.return_value
        mock_index_store.load.return_value = {"subs": []}

        # Save
        data = {
            "phone": "+123",
            "phone_code_hash": "hash",
            "session_name": "s1",
            "created_at": time.time(),
        }
        store.save_pending_otp("sub1", "bearer1", data)

        mock_sub_store.save.assert_called_once()
        saved_data = mock_sub_store.save.call_args[0][0]
        assert "bearer1" in saved_data
        assert saved_data["bearer1"]["phone"] == "+123"

        mock_index_store.save.assert_called_once_with({"subs": ["sub1"]})

        # Load
        mock_sub_store.load.return_value = {"bearer1": data}
        loaded = store.load_pending_otp("sub1", "bearer1")
        assert loaded is not None
        assert loaded["phone"] == "+123"

        # Load nonexistent bearer
        assert store.load_pending_otp("sub1", "nonexistent") is None

        # Delete
        mock_sub_store.load.return_value = {"bearer1": data}
        assert store.delete_pending_otp("sub1", "bearer1") is True

        # Delete nonexistent
        assert store.delete_pending_otp("sub1", "nonexistent") is False

    def test_load_expired_pending_otp(self):
        store = PendingOtpStore(backend=MagicMock())
        store._sub_store = MagicMock()
        mock_sub_store = store._sub_store.return_value
        store._index_store = MagicMock()

        # Expired data
        data = {
            "phone": "+123",
            "phone_code_hash": "hash",
            "session_name": "s1",
            "created_at": time.time() - 400,  # 400 seconds ago (TTL is 300)
        }
        mock_sub_store.load.return_value = {"bearer1": data}

        # Loading should purge it and return None
        loaded = store.load_pending_otp("sub1", "bearer1")
        assert loaded is None
        mock_sub_store.clear.assert_called_once()

    def test_cleanup_expired(self):
        store = PendingOtpStore(backend=MagicMock())

        store._index_store = MagicMock()
        mock_index_store = store._index_store.return_value
        mock_index_store.load.return_value = {"subs": ["sub1", "sub2"]}

        store._sub_store = MagicMock()

        def side_effect(sub):
            mock = MagicMock()
            if sub == "sub1":
                # Stale entry
                mock.load.return_value = {"b1": {"created_at": time.time() - 400}}
            else:
                # Fresh entry
                mock.load.return_value = {"b2": {"created_at": time.time()}}
            return mock

        store._sub_store.side_effect = side_effect

        removed = store.cleanup_expired()
        assert removed == 1

    def test_load_invalid_type(self):
        store = PendingOtpStore(backend=MagicMock())
        store._sub_store = MagicMock()
        mock_sub_store = store._sub_store.return_value
        mock_sub_store.load.return_value = ["not", "a", "dict"]

        assert store.load_pending_otp("sub1", "bearer1") is None

        mock_sub_store.load.return_value = {"bearer1": "not a dict"}
        assert store.load_pending_otp("sub1", "bearer1") is None

        # for cleanup
        store._index_store = MagicMock()
        mock_index_store = store._index_store.return_value
        mock_index_store.load.return_value = {"subs": ["sub1"]}

        store._sub_store.side_effect = lambda sub: MagicMock(
            load=MagicMock(return_value=["invalid"])
        )
        removed = store.cleanup_expired()
        assert removed == 0

    def test_save_empty_index_returns_list(self):
        store = PendingOtpStore(backend=MagicMock())
        store._sub_store = MagicMock()
        store._index_store = MagicMock()
        store._index_store.return_value.load.return_value = ["invalid", "index"]

        data = {
            "phone": "+123",
            "phone_code_hash": "hash",
            "session_name": "s1",
            "created_at": time.time(),
        }
        store.save_pending_otp("sub1", "bearer1", data)

    def test_delete_pending_otp_clears_store_when_empty(self):
        store = PendingOtpStore(backend=MagicMock())
        store._sub_store = MagicMock()
        mock_sub_store = store._sub_store.return_value

        data = {
            "phone": "+123",
            "phone_code_hash": "hash",
            "session_name": "s1",
            "created_at": time.time(),
        }
        mock_sub_store.load.return_value = {"bearer1": data}
        store._index_store = MagicMock()
        store._index_store.return_value.load.return_value = {"subs": ["sub1"]}

        assert store.delete_pending_otp("sub1", "bearer1") is True
        mock_sub_store.clear.assert_called_once()
