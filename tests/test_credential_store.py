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

    async def test_load_returns_none_when_no_file(self, data_dir: Path) -> None:
        """Loading from empty store returns None."""
        store = CredentialStore(data_dir, secret="test-secret")
        assert await store.load() is None

    async def test_different_secrets_produce_different_encryption(
        self, data_dir: Path
    ) -> None:
        """Different secrets should not decrypt each other's data."""
        store1 = CredentialStore(data_dir, secret="secret-one")
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        await store1.store(creds)

        # Read raw encrypted bytes
        enc_path = data_dir / "credentials.enc"
        encrypted_data = enc_path.read_bytes()

        # Try to decrypt with different secret -- should fail
        store2 = CredentialStore(data_dir, secret="secret-two")
        with pytest.raises(InvalidTag):
            await store2.load()

        # Original secret still works
        store1_again = CredentialStore(data_dir, secret="secret-one")
        assert await store1_again.load() == creds

        # Verify the encrypted file is still the same (not corrupted by failed load)
        assert enc_path.read_bytes() == encrypted_data

    async def test_delete_removes_file(self, data_dir: Path) -> None:
        """Delete should remove the credentials file."""
        store = CredentialStore(data_dir, secret="test-secret")
        creds = {"TELEGRAM_BOT_TOKEN": "token123"}
        await store.store(creds)

        enc_path = data_dir / "credentials.enc"
        assert enc_path.exists()

        await store.delete()
        assert not enc_path.exists()

    async def test_delete_noop_when_no_file(self, data_dir: Path) -> None:
        """Delete should not raise when no file exists."""
        store = CredentialStore(data_dir, secret="test-secret")
        await store.delete()  # Should not raise

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

    async def test_chmod_failure_swallowed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that OSError during chmod is silently ignored."""

        def mock_chmod(*args, **kwargs):
            raise OSError("chmod failed")

        monkeypatch.setattr("pathlib.Path.chmod", mock_chmod)

        store = CredentialStore(tmp_path)
        # Store writing triggers credential chmod
        await store.store({"api_id": "123"})
