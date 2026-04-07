from pathlib import Path
from unittest.mock import patch

import pytest

from better_telegram_mcp.transports.credential_store import CredentialStore


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


def test_credential_store_caches_salt_and_secret(data_dir: Path):
    """Test that CredentialStore caches salt and secret in memory."""
    # 1. Initial setup - create files on disk
    salt_path = (data_dir / ".salt").resolve()
    secret_path = (data_dir / ".secret").resolve()

    salt_val = b"fixed-salt-12345"
    secret_val = "fixed-secret-67890"

    salt_path.write_bytes(salt_val)
    secret_path.write_text(secret_val)

    # 2. First instantiation - should read from disk
    store1 = CredentialStore(data_dir)
    assert store1._salt == salt_val
    assert store1._secret == secret_val

    # 3. Mock Path.read_bytes and Path.read_text to detect subsequent reads
    with (
        patch.object(Path, "read_bytes") as mock_read_bytes,
        patch.object(Path, "read_text") as mock_read_text,
    ):
        # Second instantiation - should NOT read from disk (use cache)
        store2 = CredentialStore(data_dir)

        assert store2._salt == salt_val
        assert store2._secret == secret_val

        mock_read_bytes.assert_not_called()
        mock_read_text.assert_not_called()


def test_cache_is_updated_on_generation(data_dir: Path):
    """Test that cache is updated when a new salt/secret is generated."""
    # No files exist
    store1 = CredentialStore(data_dir)
    salt1 = store1._salt
    secret1 = store1._secret

    with (
        patch.object(Path, "read_bytes") as mock_read_bytes,
        patch.object(Path, "read_text") as mock_read_text,
    ):
        store2 = CredentialStore(data_dir)
        assert store2._salt == salt1
        assert store2._secret == secret1

        mock_read_bytes.assert_not_called()
        mock_read_text.assert_not_called()


def test_cache_is_updated_on_migration(data_dir: Path):
    """Test that cache is updated during legacy salt migration."""
    from better_telegram_mcp.transports.credential_store import _LEGACY_SALT

    # 1. Setup legacy state (credentials file exists, but no salt file)
    creds_path = data_dir / "credentials.enc"
    creds_path.touch()

    # Ensure cache is clear for this specific test dir
    CredentialStore.clear_cache()

    store1 = CredentialStore(data_dir, secret="test")
    assert store1._salt == _LEGACY_SALT

    # 2. Trigger migration via store()
    new_creds = {"api_id": "123"}
    store1.store(new_creds)

    migrated_salt = store1._salt
    assert migrated_salt != _LEGACY_SALT

    # 3. Next instantiation should use the migrated salt from cache
    with patch.object(Path, "read_bytes") as mock_read_bytes:
        store2 = CredentialStore(data_dir, secret="test")
        assert store2._salt == migrated_salt
        mock_read_bytes.assert_not_called()


def test_delete_clears_cache(data_dir: Path):
    """Test that delete() removes entries from the cache."""
    store1 = CredentialStore(data_dir)
    salt1 = store1._salt

    # Verify it is in cache
    assert store1._salt_path in CredentialStore._salt_cache

    # Ensure no salt file on disk so next init MUST generate new or use cache
    if store1._salt_path.exists():
        store1._salt_path.unlink()

    store1.delete()

    # Verify it is GONE from cache
    assert store1._salt_path not in CredentialStore._salt_cache

    # Next instantiation should generate new ones because they are gone from disk AND cache
    store2 = CredentialStore(data_dir)
    assert store2._salt != salt1
