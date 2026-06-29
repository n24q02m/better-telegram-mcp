"""Master-secret resolution for HTTP mode.

The persistent server secret (CREDENTIAL_SECRET env var or auto-generated)
is stored at: DATA_DIR/.secret with 0o600 permissions.
"""

import hashlib
import os
import secrets
import stat
from pathlib import Path

# POSIX: 0o600 (owner-only RW). Used by atomic_write_bytes_0600 so we never
# leave a window where the file exists with broader permissions.
_OWNER_RW = stat.S_IRUSR | stat.S_IWUSR


def _atomic_write_bytes_0600(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically with 0o600 permissions.

    Eliminates the open-then-chmod TOCTOU race that was flagged by code
    scanning: the previous flow was ``path.write_bytes(data); path.chmod(0o600)``,
    which briefly leaves the file world-readable on POSIX (the default umask
    interacts with the create syscall before chmod gets to tighten the mode).

    Strategy:
      1. ``os.open(O_CREAT|O_WRONLY|O_TRUNC, mode=0o600)`` creates the file
         with the secure mode in a single syscall (no race window). ``umask``
         can still narrow but not widen the permissions.
      2. ``O_BINARY`` is OR-ed in on Windows so the raw ``os.write`` does not
         perform LF->CRLF translation — the payload here is AES-GCM
         ciphertext and any such translation corrupts it (``pathlib``'s
         ``write_bytes`` was implicitly binary; ``os.open`` defaults to text
         mode on Windows).
      3. After write+close, ``os.chmod`` to 0o600 enforces the exact mode
         even when ``umask`` was unusually permissive or when the file
         already existed (O_CREAT|O_TRUNC truncates but preserves perms).
         ``os.chmod`` failure on non-POSIX filesystems is harmless and
         swallowed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # Windows: force binary mode so ciphertext bytes are written verbatim.
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(str(path), flags, _OWNER_RW)

    # os.open mode only applies to newly created files. We must explicitly chmod
    # to enforce permissions on existing files before writing to avoid silent truncation.
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, _OWNER_RW)
        else:
            os.chmod(str(path), _OWNER_RW)
    except OSError:
        # Windows may not support chmod / non-POSIX FS
        pass

    with os.fdopen(fd, "wb") as f:
        f.write(data)


class CredentialStore:
    """Master-secret resolution for HTTP transport mode.

    Resolves (or generates and persists) the per-install server secret.
    The secret is persisted to ``DATA_DIR/.secret`` with 0o600 permissions.
    """

    @staticmethod
    def _resolve_or_generate_secret(data_dir: Path) -> str:
        """Load persisted secret or generate a new one (atomic 0o600 write).

        Supports v2 KDF-derived secrets for improved strength while maintaining
        backward compatibility with legacy hex-only secrets.
        """

        secret_path = data_dir / ".secret"
        if secret_path.exists():
            raw = secret_path.read_text().strip()
            # Format: v2:pbkdf2:sha256:600000:<salt_hex>:<seed_hex>
            if raw.startswith("v2:pbkdf2:sha256:600000:"):
                parts = raw.split(":")
                if len(parts) == 6:
                    try:
                        salt = bytes.fromhex(parts[4])
                        seed = bytes.fromhex(parts[5])
                        # Derive operational secret (32 bytes -> 64 hex chars)
                        derived = hashlib.pbkdf2_hmac("sha256", seed, salt, 600000)
                        return derived.hex()
                    except (ValueError, IndexError):
                        # Malformed v2, fallback to raw
                        return raw
            # Legacy hex secret or malformed v2
            return raw

        # Generate new v2 secret
        salt = secrets.token_bytes(16)
        seed = secrets.token_bytes(32)

        # Format for storage: v2 prefix prevents collision with legacy hex secrets
        storage_str = f"v2:pbkdf2:sha256:600000:{salt.hex()}:{seed.hex()}"
        _atomic_write_bytes_0600(secret_path, storage_str.encode())

        # Derive initial operational secret
        derived = hashlib.pbkdf2_hmac("sha256", seed, salt, 600000)
        return derived.hex()
