from better_telegram_mcp.auth.per_user_session_store import (
    _LEGACY_SALT as PER_USER_LEGACY_SALT,
)
from better_telegram_mcp.auth.per_user_session_store import PerUserSessionStore
from better_telegram_mcp.transports.credential_store import (
    _LEGACY_SALT as CRED_STORE_LEGACY_SALT,
)
from better_telegram_mcp.transports.credential_store import CredentialStore


def test_per_user_session_store_salt_tightened(tmp_path):
    data_dir = tmp_path / "per_user"
    data_dir.mkdir()
    session_file = data_dir / "sessions.enc"

    # Empty file
    session_file.touch()
    store = PerUserSessionStore(data_dir, secret="test")
    assert store._salt != PER_USER_LEGACY_SALT

    # Non-empty file (legacy)
    data_dir_legacy = tmp_path / "per_user_legacy"
    data_dir_legacy.mkdir()
    session_file_legacy = data_dir_legacy / "sessions.enc"
    session_file_legacy.write_bytes(b"legacy-data")
    store_legacy = PerUserSessionStore(data_dir_legacy, secret="test")
    assert store_legacy._salt == PER_USER_LEGACY_SALT


def test_credential_store_salt_tightened(tmp_path):
    data_dir = tmp_path / "cred_store"
    data_dir.mkdir()
    session_file = data_dir / "credentials.enc"

    # Empty file
    session_file.touch()
    store = CredentialStore(data_dir, secret="test")
    assert store._salt != CRED_STORE_LEGACY_SALT

    # Non-empty file (legacy)
    data_dir_legacy = tmp_path / "cred_store_legacy"
    data_dir_legacy.mkdir()
    session_file_legacy = data_dir_legacy / "credentials.enc"
    session_file_legacy.write_bytes(b"legacy-data")
    store_legacy = CredentialStore(data_dir_legacy, secret="test")
    assert store_legacy._salt == CRED_STORE_LEGACY_SALT
