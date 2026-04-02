"""Tests for encrypted credential storage."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from better_telegram_mcp.transports.credential_store import CredentialStore


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


class TestCredentialStore:
    def test_store_load_roundtrip(self, data_dir: Path) -> None:
        """Credentials can be stored and loaded back correctly."""
        store = CredentialStore(data_dir, secret="test-secret")
        creds = {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_API_ID": "12345",
        }
        store.store(creds)
        loaded = store.load()
        assert loaded == creds

    def test_load_returns_none_when_no_file(self, data_dir: Path) -> None:
        """Loading from empty store returns None."""
        store = CredentialStore(data_dir, secret="test-secret")
        assert store.load() is None

    def test_different_secrets_produce_different_encryption(
        self, data_dir: Path
    ) -> None:
        """Different secrets should not decrypt each other's data."""
        store1 = CredentialStore(data_dir, secret="secret-one")
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        store1.store(creds)

        # Read raw encrypted bytes
        enc_path = data_dir / "credentials.enc"
        encrypted_data = enc_path.read_bytes()

        # Try to decrypt with different secret -- should fail
        store2 = CredentialStore(data_dir, secret="secret-two")
        with pytest.raises(InvalidTag):
            store2.load()

        # Original secret still works
        store1_again = CredentialStore(data_dir, secret="secret-one")
        assert store1_again.load() == creds

        # Verify the encrypted file is still the same (not corrupted by failed load)
        assert enc_path.read_bytes() == encrypted_data

    def test_delete_removes_file(self, data_dir: Path) -> None:
        """Delete should remove the credentials file."""
        store = CredentialStore(data_dir, secret="test-secret")
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        store.store(creds)

        enc_path = data_dir / "credentials.enc"
        assert enc_path.exists()

        store.delete()
        assert not enc_path.exists()

    def test_delete_noop_when_no_file(self, data_dir: Path) -> None:
        """Delete should not raise when no file exists."""
        store = CredentialStore(data_dir, secret="test-secret")
        store.delete()  # Should not raise

    def test_auto_generated_secret_persists(self, data_dir: Path) -> None:
        """Auto-generated secret should be saved and reused across instances."""
        store1 = CredentialStore(data_dir)
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        store1.store(creds)

        # New instance should auto-load the persisted secret
        store2 = CredentialStore(data_dir)
        assert store2.load() == creds

    def test_auto_generated_secret_file_created(self, data_dir: Path) -> None:
        """Secret file should be created when no secret is provided."""
        CredentialStore(data_dir)
        secret_path = data_dir / ".secret"
        assert secret_path.exists()
        secret = secret_path.read_text().strip()
        assert len(secret) == 64  # 32 bytes hex-encoded

    def test_env_var_secret_takes_precedence(
        self, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CREDENTIAL_SECRET env var should be used when set."""
        monkeypatch.setenv("CREDENTIAL_SECRET", "env-secret")
        store = CredentialStore(data_dir)
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        store.store(creds)

        # Should load with same env var
        store2 = CredentialStore(data_dir)
        assert store2.load() == creds

        # Should not load without env var (different auto-generated secret)
        monkeypatch.delenv("CREDENTIAL_SECRET")
        store3 = CredentialStore(data_dir)
        # Auto-generated secret is different from "env-secret"
        with pytest.raises(InvalidTag):
            store3.load()

    def test_store_overwrites_existing(self, data_dir: Path) -> None:
        """Storing new credentials should overwrite old ones."""
        store = CredentialStore(data_dir, secret="test-secret")
        store.store({"TELEGRAM_BOT_TOKEN": "old-token"})
        store.store({"TELEGRAM_BOT_TOKEN": "new-token"})
        assert store.load() == {"TELEGRAM_BOT_TOKEN": "new-token"}

    def test_empty_credentials(self, data_dir: Path) -> None:
        """Empty dict should be storable and loadable."""
        store = CredentialStore(data_dir, secret="test-secret")
        store.store({})
        assert store.load() == {}

    def test_data_dir_created_if_missing(self, tmp_path: Path) -> None:
        """Store should create data_dir if it does not exist."""
        nested = tmp_path / "a" / "b" / "c"
        store = CredentialStore(nested, secret="test-secret")
        store.store({"key": "value"})
        assert store.load() == {"key": "value"}

    def test_chmod_failure_swallowed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that OSError during chmod is silently ignored."""

        def mock_chmod(*args, **kwargs):
            raise OSError("chmod failed")

        monkeypatch.setattr("pathlib.Path.chmod", mock_chmod)

        store = CredentialStore(tmp_path)
        # Store writing triggers credential chmod
        store.store({"api_id": "123"})

    def test_random_salt_generation(self, data_dir: Path) -> None:
        """New installation should generate a random salt file."""
        store = CredentialStore(data_dir, secret="test-secret")
        salt_path = data_dir / ".salt"
        assert salt_path.exists()
        salt = salt_path.read_bytes()
        assert len(salt) == 16
        assert store._salt == salt

    def test_auto_generated_salt_persists(self, data_dir: Path) -> None:
        """Salt should be saved and reused across instances."""
        CredentialStore(data_dir)
        salt = (data_dir / ".salt").read_bytes()

        store2 = CredentialStore(data_dir)
        assert store2._salt == salt

    def test_legacy_salt_migration(self, data_dir: Path) -> None:
        """Should load legacy data and migrate to new salt on store."""
        import json
        import os

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        secret = "legacy-secret"
        legacy_salt = b"mcp-telegram-creds"
        creds = {"token": "legacy-token"}

        # 1. Manually create legacy encrypted file
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=legacy_salt,
            iterations=100_000,
        )
        key = kdf.derive(secret.encode())
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, json.dumps(creds).encode(), None)
        (data_dir / "credentials.enc").write_bytes(nonce + ciphertext)

        # 2. Load with CredentialStore (should fallback to legacy salt)
        store = CredentialStore(data_dir, secret=secret)
        assert store._salt == legacy_salt
        assert store.load() == creds
        assert not (data_dir / ".salt").exists()

        # 3. Store new data (should trigger migration)
        new_creds = {"token": "new-token"}
        store.store(new_creds)

        assert (data_dir / ".salt").exists()
        assert store._salt != legacy_salt
        assert store.load() == new_creds

        # 4. Verify new instances use the new salt
        store2 = CredentialStore(data_dir, secret=secret)
        assert store2._salt == store._salt
        assert store2.load() == new_creds
