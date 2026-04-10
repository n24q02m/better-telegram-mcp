"""Tests for secret caching in Settings and storage classes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.credential_store import CredentialStore


def test_settings_secret_caching(tmp_path: Path) -> None:
    """Settings.secret should only read the secret file once."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    secret_path = data_dir / ".secret"
    secret_path.write_text("test-secret-value")

    settings = Settings(data_dir=data_dir)

    # Patch the utility function in the config module
    with patch("better_telegram_mcp.config.resolve_or_generate_secret") as mock_resolve:
        mock_resolve.return_value = "mock-secret"

        # First access
        s1 = settings.secret
        assert s1 == "mock-secret"
        assert mock_resolve.call_count == 1

        # Second access
        s2 = settings.secret
        assert s2 == "mock-secret"
        # cached_property should prevent second call to mock_resolve
        assert mock_resolve.call_count == 1


def test_credential_store_uses_cached_secret(tmp_path: Path) -> None:
    """CredentialStore should use the secret from Settings if provided."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    settings = Settings(data_dir=data_dir)
    # Trigger secret generation/load
    secret = settings.secret

    with patch(
        "better_telegram_mcp.transports.credential_store.resolve_or_generate_secret"
    ) as mock_resolve:
        # If we pass the secret, it should NOT call resolve_or_generate_secret
        store = CredentialStore(data_dir, secret=secret)
        assert store._secret == secret
        assert mock_resolve.call_count == 0

        # If we DON'T pass the secret, it SHOULD call it
        _ = CredentialStore(data_dir)
        assert mock_resolve.call_count == 1
