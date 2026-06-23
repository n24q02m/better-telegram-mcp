"""Tests for asynchronous master-secret resolution and atomic 0o600 writes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.credential_store import (
    CredentialStore,
    async_atomic_write_bytes_0600,
)

# POSIX file mode bits (0o600) are not meaningful on Windows
posix_only = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX file mode bits (0o600) are not enforced on Windows",
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


class TestAsyncResolveOrGenerateSecret:
    async def test_generates_and_persists_secret_async(self, data_dir: Path) -> None:
        """First call generates a secret; later calls reuse the persisted one."""
        secret = await CredentialStore.async_resolve_or_generate_secret(data_dir)
        secret_path = data_dir / ".secret"
        assert secret_path.exists()
        assert secret_path.read_text().strip() == secret
        assert len(secret) == 64  # 32 bytes hex-encoded

        # Second call returns the same persisted secret.
        assert (
            await CredentialStore.async_resolve_or_generate_secret(data_dir) == secret
        )

    async def test_settings_async_secret(self, data_dir: Path) -> None:
        """Settings.async_secret correctly resolves and caches the secret."""
        settings = Settings(data_dir=data_dir)

        # Resolve via async_secret
        secret = await settings.async_secret()
        assert len(secret) == 64

        # Verify it's cached in the 'secret' property
        assert settings.secret == secret

        # Verify further async calls return the same
        assert await settings.async_secret() == secret


class TestAsyncAtomicWrite:
    @posix_only
    async def test_async_atomic_write_is_0o600(self, tmp_path: Path) -> None:
        import os
        import stat

        target = tmp_path / "async_secret.bin"
        await async_atomic_write_bytes_0600(target, b"async-secure")

        assert target.read_bytes() == b"async-secure"
        mode = stat.S_IMODE(os.stat(target).st_mode)
        assert mode == 0o600, f"expected 0o600, got 0o{mode:o}"

    async def test_async_atomic_write_creates_with_secure_mode(
        self, tmp_path: Path
    ) -> None:
        """Verify async_atomic_write_bytes_0600 calls _atomic_write_bytes_0600."""
        from unittest.mock import patch

        target = tmp_path / "test.bin"

        # We patch the sync version to verify it's called
        with patch(
            "better_telegram_mcp.transports.credential_store._atomic_write_bytes_0600"
        ) as mock_sync_write:
            await async_atomic_write_bytes_0600(target, b"hello")
            mock_sync_write.assert_called_once_with(target, b"hello")
