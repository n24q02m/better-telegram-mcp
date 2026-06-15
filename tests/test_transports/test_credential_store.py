"""Tests for master-secret resolution and atomic 0o600 writes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


class TestResolveOrGenerateSecret:
    def test_generates_and_persists_secret(self, data_dir: Path) -> None:
        """First call generates a secret; later calls reuse the persisted one."""
        secret = CredentialStore._resolve_or_generate_secret(data_dir)
        secret_path = data_dir / ".secret"
        assert secret_path.exists()
        assert secret_path.read_text().strip() == secret
        assert len(secret) == 64  # 32 bytes hex-encoded

        # Second call returns the same persisted secret.
        assert CredentialStore._resolve_or_generate_secret(data_dir) == secret


class TestAtomicWriteTOCTOU:
    """Verify the open-then-chmod TOCTOU window is closed.

    The previous implementation did ``path.write_bytes(data)`` followed by
    ``path.chmod(0o600)``. Between those two syscalls the file existed
    with the process ``umask``-derived permissions (commonly 0o644), so a
    co-tenant on the host could open() the file before the chmod landed
    and read the persisted secret. The fix is to create the file with mode
    0o600 in a single ``os.open()`` call.
    """

    @posix_only
    def test_secret_file_is_0o600_immediately(self, tmp_path: Path) -> None:
        import os
        import stat

        data_dir = tmp_path / "fresh"
        data_dir.mkdir()
        # Auto-generated secret writes .secret to disk.
        CredentialStore._resolve_or_generate_secret(data_dir)

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
        """Re-writing must reset perms even if a stale loose-perm file existed."""
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
