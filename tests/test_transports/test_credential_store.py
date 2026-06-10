import os
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.exceptions import InvalidTag

from better_telegram_mcp.transports.credential_store import CredentialStore

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX only")


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "credentials"
    d.mkdir()
    return d


class TestCredentialStore:
    async def test_store_and_load(self, data_dir: Path) -> None:
        """Credentials should be encrypted, saved, and loadable."""
        store = CredentialStore(data_dir, secret="test-secret")
        creds = {"TELEGRAM_BOT_TOKEN": "123:ABC"}
        await store.store(creds)

        # New instance with same secret should be able to load
        store2 = CredentialStore(data_dir, secret="test-secret")
        loaded = await store2.load()
        assert loaded == creds

    async def test_load_non_existent(self, data_dir: Path) -> None:
        """Loading from a non-existent file should return None."""
        store = CredentialStore(data_dir, secret="test-secret")
        assert await store.load() is None

    async def test_load_wrong_secret(self, data_dir: Path) -> None:
        """Loading with a different secret should fail."""
        store1 = CredentialStore(data_dir, secret="secret-one")
        await store1.store({"key": "val"})

        store2 = CredentialStore(data_dir, secret="secret-two")
        with pytest.raises(InvalidTag):
            await store2.load()

    async def test_delete(self, data_dir: Path) -> None:
        """Delete should remove the credentials file."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({"key": "val"})
        assert (data_dir / "credentials.enc").exists()

        store.delete()
        assert not (data_dir / "credentials.enc").exists()
        assert await store.load() is None

    async def test_memoization(self, data_dir: Path) -> None:
        """Key derivation and file loading should be memoized."""
        store = CredentialStore(data_dir, secret="test-secret")
        creds = {"TELEGRAM_BOT_TOKEN": "123:ABC"}
        await store.store(creds)

        # Clear cache to force load from disk
        store._cached_credentials = None

        # Mock Path.read_bytes to track calls
        with patch(
            "pathlib.Path.read_bytes", wraps=store._path.read_bytes
        ) as mock_read:
            # First load
            creds1 = await store.load()
            assert creds1 is not None
            assert creds1["TELEGRAM_BOT_TOKEN"] == "123:ABC"
            assert mock_read.call_count == 1

            # Second load uses cache
            creds2 = await store.load()
            assert creds2 is not None
            assert creds2["TELEGRAM_BOT_TOKEN"] == "123:ABC"
            assert mock_read.call_count == 1

    async def test_auto_generated_secret_persists(self, data_dir: Path) -> None:
        """Auto-generated secret should be saved and reused across instances."""
        store1 = CredentialStore(data_dir)
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        await store1.store(creds)

        # New instance should auto-load the persisted secret
        store2 = CredentialStore(data_dir)
        assert await store2.load() == creds

    def test_auto_generated_secret_file_created(self, data_dir: Path) -> None:
        """Secret file should be created when no secret is provided."""
        CredentialStore(data_dir)
        secret_path = data_dir / ".secret"
        assert secret_path.exists()
        secret = secret_path.read_text().strip()
        assert len(secret) == 64  # 32 bytes hex-encoded

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

    async def test_store_overwrites_existing(self, data_dir: Path) -> None:
        """Storing new credentials should overwrite old ones."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({"TELEGRAM_BOT_TOKEN": "old-token"})
        await store.store({"TELEGRAM_BOT_TOKEN": "new-token"})
        assert await store.load() == {"TELEGRAM_BOT_TOKEN": "new-token"}

    async def test_empty_credentials(self, data_dir: Path) -> None:
        """Empty dict should be storable and loadable."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.store({})
        assert await store.load() == {}

    async def test_data_dir_created_if_missing(self, tmp_path: Path) -> None:
        """Store should create data_dir if it does not exist."""
        nested = tmp_path / "a" / "b" / "c"
        store = CredentialStore(nested, secret="test-secret")
        await store.store({"key": "value"})
        assert await store.load() == {"key": "value"}

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

    def test_random_salt_for_new_install(self, data_dir: Path) -> None:
        """New installation should generate random salt, not use legacy."""
        from better_telegram_mcp.transports.credential_store import _LEGACY_SALT

        store = CredentialStore(data_dir, secret="test-secret")
        assert store._salt != _LEGACY_SALT
        salt_path = data_dir / ".salt"
        assert salt_path.exists()
        assert len(store._salt) == 16

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
    def test_salt_file_is_0o600_immediately(self, data_dir: Path) -> None:
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
    def test_secret_file_is_0o600_immediately(self, tmp_path: Path) -> None:
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

    def test_atomic_write_creates_with_secure_mode_not_default_umask(
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
    def test_atomic_write_overwrites_existing_file_with_secure_mode(
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
