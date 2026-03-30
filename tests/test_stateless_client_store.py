"""Tests for StatelessClientStore (HMAC-based DCR)."""

from __future__ import annotations

import pytest

from better_telegram_mcp.auth.stateless_client_store import (
    ClientInfo,
    StatelessClientStore,
)


@pytest.fixture
def store() -> StatelessClientStore:
    return StatelessClientStore("test-secret-key")


class TestStatelessClientStore:
    def test_register_returns_tuple(self, store: StatelessClientStore) -> None:
        """Register should return (client_id, client_secret) tuple."""
        client_id, client_secret = store.register(
            ["http://localhost/callback"], "TestApp"
        )
        assert isinstance(client_id, str)
        assert isinstance(client_secret, str)
        assert len(client_id) == 32
        assert len(client_secret) == 64  # Full SHA256 hex

    def test_register_deterministic(self, store: StatelessClientStore) -> None:
        """Same input always produces same credentials (idempotent)."""
        uris = ["http://localhost/callback"]
        name = "TestApp"

        id1, secret1 = store.register(uris, name)
        id2, secret2 = store.register(uris, name)

        assert id1 == id2
        assert secret1 == secret2

    def test_different_inputs_different_ids(self, store: StatelessClientStore) -> None:
        """Different inputs produce different client_ids."""
        id1, _ = store.register(["http://localhost/a"], "App1")
        id2, _ = store.register(["http://localhost/b"], "App2")
        assert id1 != id2

    def test_different_uris_same_name(self, store: StatelessClientStore) -> None:
        """Different redirect_uris produce different client_ids."""
        id1, _ = store.register(["http://a.example.com"], "Same")
        id2, _ = store.register(["http://b.example.com"], "Same")
        assert id1 != id2

    def test_same_uris_different_name(self, store: StatelessClientStore) -> None:
        """Different client_name produces different client_ids."""
        uri = ["http://localhost/callback"]
        id1, _ = store.register(uri, "App1")
        id2, _ = store.register(uri, "App2")
        assert id1 != id2

    def test_different_secrets_different_results(self) -> None:
        """Different HMAC secrets produce different credentials."""
        store1 = StatelessClientStore("secret-one")
        store2 = StatelessClientStore("secret-two")

        uris = ["http://localhost/callback"]
        id1, secret1 = store1.register(uris, "App")
        id2, secret2 = store2.register(uris, "App")

        assert id1 != id2
        assert secret1 != secret2

    def test_get_returns_cached_client(self, store: StatelessClientStore) -> None:
        """Get should return full ClientInfo for registered clients."""
        uris = ["http://localhost/callback"]
        name = "TestApp"
        client_id, client_secret = store.register(uris, name)

        info = store.get(client_id)
        assert info is not None
        assert info.client_id == client_id
        assert info.client_secret == client_secret
        assert info.redirect_uris == uris
        assert info.client_name == name

    def test_get_unknown_returns_fallback(self, store: StatelessClientStore) -> None:
        """Get for unregistered client_id returns fallback with empty redirect_uris."""
        info = store.get("unknown-client-id")
        assert info is not None
        assert info.client_id == "unknown-client-id"
        assert info.redirect_uris == []
        # Secret is still derived (consistent with HMAC)
        assert isinstance(info.client_secret, str)

    def test_get_fallback_secret_matches(self, store: StatelessClientStore) -> None:
        """Fallback client_secret should match what register would produce."""
        uris = ["http://localhost/callback"]
        client_id, client_secret = store.register(uris, "App")

        # Create new store (no cache) with same secret
        fresh_store = StatelessClientStore("test-secret-key")
        info = fresh_store.get(client_id)

        assert info is not None
        assert info.client_secret == client_secret

    def test_validate_secret_correct(self, store: StatelessClientStore) -> None:
        """Validate should return True for correct client_secret."""
        client_id, client_secret = store.register(["http://localhost"], "App")
        assert store.validate_secret(client_id, client_secret) is True

    def test_validate_secret_wrong(self, store: StatelessClientStore) -> None:
        """Validate should return False for wrong client_secret."""
        client_id, _ = store.register(["http://localhost"], "App")
        assert store.validate_secret(client_id, "wrong-secret") is False

    def test_validate_secret_timing_safe(self, store: StatelessClientStore) -> None:
        """Validate uses hmac.compare_digest (timing-safe comparison)."""
        # This is an implementation detail test - verify it's callable
        # and returns consistent results
        client_id, client_secret = store.register(["http://localhost"], "App")
        for _ in range(100):
            assert store.validate_secret(client_id, client_secret) is True
            assert store.validate_secret(client_id, "x" * 64) is False

    def test_register_empty_uris(self, store: StatelessClientStore) -> None:
        """Register with empty redirect_uris should work."""
        client_id, client_secret = store.register([], None)
        assert len(client_id) == 32
        info = store.get(client_id)
        assert info is not None
        assert info.redirect_uris == []
        assert info.client_name is None

    def test_register_multiple_uris(self, store: StatelessClientStore) -> None:
        """Register with multiple redirect_uris should work."""
        uris = ["http://localhost/a", "http://localhost/b", "http://localhost/c"]
        client_id, _ = store.register(uris, "MultiRedirect")
        info = store.get(client_id)
        assert info is not None
        assert info.redirect_uris == uris

    def test_client_info_defaults(self) -> None:
        """ClientInfo should have sensible defaults."""
        info = ClientInfo(
            client_id="test",
            client_secret="secret",
            redirect_uris=["http://localhost"],
        )
        assert info.grant_types == ["authorization_code", "refresh_token"]
        assert info.response_types == ["code"]
        assert info.token_endpoint_auth_method == "client_secret_post"
        assert info.client_name is None

    def test_cache_survives_multiple_registers(
        self, store: StatelessClientStore
    ) -> None:
        """Cache should hold all registered clients."""
        ids = set()
        for i in range(10):
            cid, _ = store.register([f"http://app{i}.example.com"], f"App{i}")
            ids.add(cid)

        assert len(ids) == 10

        for cid in ids:
            info = store.get(cid)
            assert info is not None
            assert info.client_id == cid
            assert len(info.redirect_uris) == 1
