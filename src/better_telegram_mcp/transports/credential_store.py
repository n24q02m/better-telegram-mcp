"""Encrypted credential storage for HTTP mode.

Credentials stored at: DATA_DIR/credentials.enc
Key derived from server secret (CREDENTIAL_SECRET env var or auto-generated).
"""

from __future__ import annotations

import copy
import json
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_LEGACY_SALT = b"mcp-telegram-creds"
_KDF_ITERATIONS = 600_000
_NONCE_SIZE = 12

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
    """Server-side encrypted credential storage.

    Used in HTTP transport mode to persist Telegram credentials
    received via the relay page.
    """

    def __init__(self, data_dir: Path, secret: str | None = None) -> None:
        self._path = data_dir / "credentials.enc"
        self._salt_path = data_dir / ".salt"
        self._secret = secret or os.environ.get("CREDENTIAL_SECRET", "")
        if not self._secret:
            self._secret = self._resolve_or_generate_secret(data_dir)
        self._salt = self._resolve_salt()
        # Cache derived key to avoid repeated 100k iteration PBKDF2 (~60ms) overhead
        self._cached_key: bytes | None = None
        self._cached_credentials: dict[str, str] | None = None

    def _resolve_salt(self) -> bytes:
        """Load persisted salt, fallback to legacy, or generate new one."""
        if self._salt_path.exists():
            return self._salt_path.read_bytes()

        # Backward compatibility: existing credentials use legacy hardcoded salt
        if self._path.exists():
            return _LEGACY_SALT

        # New installation: generate random salt and persist atomically
        # with 0o600 (no open->chmod TOCTOU window).
        salt = os.urandom(16)
        _atomic_write_bytes_0600(self._salt_path, salt)
        return salt

    @staticmethod
    def _resolve_or_generate_secret(data_dir: Path) -> str:
        """Load persisted secret or generate a new one (atomic 0o600 write)."""
        secret_path = data_dir / ".secret"
        if secret_path.exists():
            return secret_path.read_text().strip()
        secret = os.urandom(32).hex()
        _atomic_write_bytes_0600(secret_path, secret.encode())
        return secret

    def _derive_key(self) -> bytes:
        if self._cached_key is not None:
            return self._cached_key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=_KDF_ITERATIONS,
        )
        self._cached_key = kdf.derive(self._secret.encode())
        return self._cached_key

    def store(self, credentials: dict[str, str]) -> None:
        """Encrypt and save credentials atomically with 0o600 permissions.

        Replaces the prior write-then-chmod sequence (which left a TOCTOU
        window where the encrypted blob existed with default umask perms
        before chmod ran).
        """
        # Migrate from legacy hardcoded salt to random salt on re-encryption.
        if self._salt == _LEGACY_SALT:
            new_salt = os.urandom(16)
            _atomic_write_bytes_0600(self._salt_path, new_salt)
            self._salt = new_salt
            self._cached_key = None  # Force re-derivation

        key = self._derive_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(_NONCE_SIZE)
        plaintext = json.dumps(credentials).encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        self._cached_credentials = copy.deepcopy(credentials)
        _atomic_write_bytes_0600(self._path, nonce + ciphertext)

    def load(self) -> dict[str, str] | None:
        """Load and decrypt credentials. Returns None if not found."""
        if self._cached_credentials is not None:
            return copy.deepcopy(self._cached_credentials)
        if not self._path.exists():
            return None
        key = self._derive_key()
        data = self._path.read_bytes()
        nonce, ciphertext = data[:_NONCE_SIZE], data[_NONCE_SIZE:]
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        self._cached_credentials = json.loads(plaintext)
        return copy.deepcopy(self._cached_credentials)

    def delete(self) -> None:
        """Delete stored credentials."""
        self._cached_credentials = None
        if self._path.exists():
            self._path.unlink()
