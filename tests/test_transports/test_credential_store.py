"""Tests for encrypted credential storage."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.exceptions import InvalidTag

from better_telegram_mcp.transports.credential_store import CredentialStore

# POSIX file mode bits (0o600) are not meaningful on Windows -- os.chmod()
# there only toggles the read-only bit. Tests that assert an exact mode are
# POSIX-only; the atomic-write behaviour itself is still exercised on Windows
# by test_atomic_write_creates_with_secure_mode_not_default_umask.
posix_only = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX file mode bits (0o600) are not enforced on Windows",
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


class TestCredentialStore:
    @pytest.mark.asyncio
    async def test_store_load_roundtrip(self, data_dir: Path) -> None:
        """Credentials can be stored and loaded back correctly."""
        store = CredentialStore(data_dir, secret="test-secret")
        creds = {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_API_ID": "12345",
        }
        await store.store(creds)
        loaded = await store.load()
        assert loaded == creds

    @pytest.mark.asyncio
    async def test_load_returns_none_when_no_file(self, data_dir: Path) -> None:
        """Loading from empty store returns None."""
        store = CredentialStore(data_dir, secret="test-secret")
        assert await store.load() is None

    @pytest.mark.asyncio
    async def test_different_secrets_produce_different_encryption(
        self, data_dir: Path
    ) -> None:
        """Data encrypted with one secret cannot be decrypted by another."""
        store1 = CredentialStore(data_dir, secret="secret-one")
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        await store1.store(creds)

        store2 = CredentialStore(data_dir, secret="secret-two")
        with pytest.raises(InvalidTag):
            await store2.load()

        # Same secret works
        store1_again = CredentialStore(data_dir, secret="secret-one")
        assert await store1_again.load() == creds

    @pytest.mark.asyncio
    async def test_delete_credentials(self, data_dir: Path) -> None:
        """Delete should remove the file and clear cache."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({"key": "value"})
        assert (data_dir / "credentials.enc").exists()

        await store.delete()
        assert not (data_dir / "credentials.enc").exists()
        assert await store.load() is None

    @pytest.mark.asyncio
    async def test_cache_usage(self, data_dir: Path) -> None:
        """Load should use cached value if available."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({"TELEGRAM_BOT_TOKEN": "123:ABC"})

        with patch(
            "better_telegram_mcp.transports.credential_store.asyncio.to_thread"
        ) as mock_to_thread:
            # We need to simulate the success of the first load
            # and then check if the second load calls to_thread.
            real_data = store._path.read_bytes()

            async def side_effect(func, *args, **kwargs):
                if func == store._path.read_bytes:
                    return real_data
                return await asyncio.to_thread(func, *args, **kwargs)

            import asyncio

            mock_to_thread.side_effect = side_effect

            # First load after cache clear
            store._cached_credentials = None
            creds1 = await store.load()
            assert creds1 is not None
            assert creds1["TELEGRAM_BOT_TOKEN"] == "123:ABC"

            # Reset mock to check for second load
            mock_to_thread.reset_mock()

            # Second load uses cache
            creds2 = await store.load()
            assert creds2 is not None
            assert creds2["TELEGRAM_BOT_TOKEN"] == "123:ABC"
            # In cache-hit scenario, it shouldn't even reach the exists() check
            # but load() calls exists() if cache is missing.
            # Actually, our load() code is:
            # if self._cached_credentials is not None: return copy.deepcopy(self._cached_credentials)
            # So if it's cached, it returns immediately.
            assert mock_to_thread.call_count == 0

    @pytest.mark.asyncio
    async def test_auto_generated_secret_persists(self, data_dir: Path) -> None:
        """Auto-generated secret should be saved and reused across instances."""
        store1 = CredentialStore(data_dir)
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        await store1.store(creds)

        # New instance should auto-load the persisted secret
        store2 = CredentialStore(data_dir)
        assert await store2.load() == creds

    @pytest.mark.asyncio
    async def test_auto_generated_secret_file_created(self, data_dir: Path) -> None:
        """Secret file should be created when no secret is provided."""
        CredentialStore(data_dir)
        secret_path = data_dir / ".secret"
        assert secret_path.exists()
        secret = secret_path.read_text().strip()
        assert len(secret) == 64  # 32 bytes hex-encoded

    @pytest.mark.asyncio
    async def test_env_var_secret_takes_precedence(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CREDENTIAL_SECRET env var should be used when set."""
        monkeypatch.setenv("CREDENTIAL_SECRET", "env-secret")
        store = CredentialStore(data_dir)
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        await store.store(creds)

        # Should load with same env var
        store2 = CredentialStore(data_dir)
        assert await store2.load() == creds

        # Should not load without env var (different auto-generated secret)
        monkeypatch.delenv("CREDENTIAL_SECRET")
        store3 = CredentialStore(data_dir)
        # Auto-generated secret is different from "env-secret"
        with pytest.raises(InvalidTag):
            await store3.load()

    @pytest.mark.asyncio
    async def test_store_overwrites_existing(self, data_dir: Path) -> None:
        """Storing new credentials should overwrite old ones."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({"TELEGRAM_BOT_TOKEN": "old-token"})
        await store.store({"TELEGRAM_BOT_TOKEN": "new-token"})
        assert await store.load() == {"TELEGRAM_BOT_TOKEN": "new-token"}

    @pytest.mark.asyncio
    async def test_empty_credentials(self, data_dir: Path) -> None:
        """Empty dict should be storable and loadable."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({})
        assert await store.load() == {}

    @pytest.mark.asyncio
    async def test_data_dir_created_if_missing(self, tmp_path: Path) -> None:
        """Store should create data_dir if it does not exist."""
        nested = tmp_path / "a" / "b" / "c"
        store = CredentialStore(nested, secret="test-secret")
        await store.store({"key": "value"})
        assert await store.load() == {"key": "value"}

    @pytest.mark.asyncio
    async def test_legacy_salt_migration(self, data_dir: Path) -> None:
        """Credentials stored with legacy hardcoded salt should be loadable,
        and re-storing should migrate to a random salt."""
        from better_telegram_mcp.transports.credential_store import _LEGACY_SALT

        store = CredentialStore(data_dir, secret="test-secret")
        # Simulate legacy: write credentials with legacy salt
        # (new install creates random salt, so we need to force legacy)
        store._salt = _LEGACY_SALT
        store._cached_key = None
        # Write a credentials file (using legacy salt)
        creds = {"TELEGRAM_BOT_TOKEN": "legacy-token"}
        # Manually encrypt and write without triggering migration
        import json
        import os

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = await store._derive_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        plaintext = json.dumps(creds).encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        store._path.write_bytes(nonce + ciphertext)

        # Remove salt file to simulate legacy state
        salt_path = data_dir / ".salt"
        if salt_path.exists():
            salt_path.unlink()

        # Create new store -- should detect legacy salt (creds exist, no .salt)
        store2 = CredentialStore(data_dir, secret="test-secret")
        assert store2._salt == _LEGACY_SALT
        loaded = await store2.load()
        assert loaded == creds

        # Re-store should trigger salt migration
        await store2.store(creds)
        assert store2._salt != _LEGACY_SALT
        assert salt_path.exists()

        # New store should use the migrated salt
        store3 = CredentialStore(data_dir, secret="test-secret")
        assert store3._salt != _LEGACY_SALT
        assert await store3.load() == creds

    @pytest.mark.asyncio
    async def test_random_salt_for_new_install(self, data_dir: Path) -> None:
        """New installation should generate random salt, not use legacy."""
        from better_telegram_mcp.transports.credential_store import _LEGACY_SALT

        store = CredentialStore(data_dir, secret="test-secret")
        assert store._salt != _LEGACY_SALT
        salt_path = data_dir / ".salt"
        assert salt_path.exists()
        assert len(store._salt) == 16

    @pytest.mark.asyncio
    async def test_chmod_failure_swallowed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that OSError during chmod is silently ignored."""

        def mock_chmod(*args, **kwargs):
            raise OSError("chmod failed")

        monkeypatch.setattr("pathlib.Path.chmod", mock_chmod)
        monkeypatch.setattr("os.chmod", mock_chmod)

        store = CredentialStore(tmp_path)
        # Store writing triggers credential chmod
        await store.store({"api_id": "123"})


class TestAtomicWriteTOCTOU:
    """Verify the open-then-chmod TOCTOU window is closed.

    The previous implementation did ``path.write_bytes(data)`` followed by
    ``path.chmod(0o600)``. Between those two syscalls the file existed
    with the process ``umask``-derived permissions (commonly 0o644), so a
    co-tenant on the host could open() the file before the chmod landed
    and read the encrypted credential blob (or the secret salt). The fix
    is to create the file with mode 0o600 in a single ``os.open()`` call.
    """

    @posix_only
    @pytest.mark.asyncio
    async def test_credentials_file_is_0o600_immediately(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """File must never exist with broader perms than 0o600."""
        import os
        import stat

        # Force a deliberately permissive umask so the OLD code path
        # would have created the file world-readable before chmod ran.
        monkeypatch.setattr(os, "umask", lambda _mask: 0o000)

        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({"TELEGRAM_BOT_TOKEN": "secret"})

        enc_path = data_dir / "credentials.enc"
        mode = stat.S_IMODE(os.stat(enc_path).st_mode)
        # 0o600 == owner R/W only (no group/other access)
        assert mode == 0o600, f"expected 0o600, got 0o{mode:o}"

    @posix_only
    @pytest.mark.asyncio
    async def test_salt_file_is_0o600_immediately(self, data_dir: Path) -> None:
        import os
        import stat

        # Trigger fresh installation (no legacy file). _resolve_salt
        # generates and writes a random salt.
        CredentialStore(data_dir, secret="test-secret")

        salt_path = data_dir / ".salt"
        assert salt_path.exists()
        mode = stat.S_IMODE(os.stat(salt_path).st_mode)
        assert mode == 0o600, f"expected 0o600, got 0o{mode:o}"

    @posix_only
    @pytest.mark.asyncio
    async def test_secret_file_is_0o600_immediately(self, tmp_path: Path) -> None:
        import os
        import stat

        data_dir = tmp_path / "fresh"
        data_dir.mkdir()
        # Auto-generated secret (no CREDENTIAL_SECRET env var, no explicit
        # secret kwarg) writes .secret to disk.
        CredentialStore(data_dir)

        secret_path = data_dir / ".secret"
        assert secret_path.exists()
        mode = stat.S_IMODE(os.stat(secret_path).st_mode)
        assert mode == 0o600, f"expected 0o600, got 0o{mode:o}"

    @pytest.mark.asyncio
    async def test_atomic_write_creates_with_secure_mode_not_default_umask(
        self, tmp_path: Path
    ) -> None:
        """``_atomic_write_bytes_0600`` must specify mode at os.open time.

        Regression guard against reverting to ``path.write_bytes`` + chmod.
        We intercept ``os.open`` and assert mode bits are 0o600.
        """
        import os

        from better_telegram_mcp.transports.credential_store import (
            _atomic_write_bytes_0600,
        )

        captured: list[int] = []
        real_open = os.open

        def spy_open(path, flags, mode=0o777):
            captured.append(mode)
            return real_open(path, flags, mode)

        target = tmp_path / "secret.bin"
        original_open = os.open
        try:
            os.open = spy_open  # type: ignore[assignment]
            _atomic_write_bytes_0600(target, b"hello")
        finally:
            os.open = original_open  # type: ignore[assignment]

        assert captured, "os.open was not called -- atomic write bypassed"
        # The single os.open() call for our target must request 0o600.
        # (We may also intercept temp/parent dir creations; ours is the one
        # creating the file at `target`.)
        assert 0o600 in captured

    @posix_only
    @pytest.mark.asyncio
    async def test_atomic_write_overwrites_existing_file_with_secure_mode(
        self, tmp_path: Path
    ) -> None:
        """Re-storing must reset perms even if a stale loose-perm file existed."""
        import os
        import stat

        from better_telegram_mcp.transports.credential_store import (
            _atomic_write_bytes_0600,
        )

        target = tmp_path / "stale.bin"
        target.write_bytes(b"old")
        os.chmod(target, 0o644)  # Simulate stale loose permissions

        _atomic_write_bytes_0600(target, b"new")

        assert target.read_bytes() == b"new"
        mode = stat.S_IMODE(os.stat(target).st_mode)
        assert mode == 0o600
