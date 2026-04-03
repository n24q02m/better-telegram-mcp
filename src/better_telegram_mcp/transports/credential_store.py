"""Encrypted credential storage for HTTP mode.

Credentials stored at: DATA_DIR/credentials.enc
Key derived from server secret (CREDENTIAL_SECRET env var or auto-generated).
Uses an embedded salt approach for secure and atomic storage.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_LEGACY_SALT = b"mcp-telegram-creds"
_KDF_ITERATIONS = 100_000
_NONCE_SIZE = 12
_SALT_SIZE = 16
_SALT_PREFIX = b"SALT"


class CredentialStore:
    """Server-side encrypted credential storage.

    Used in HTTP transport mode to persist Telegram credentials
    received via the relay page.
    """

    def __init__(self, data_dir: Path, secret: str | None = None) -> None:
        self._path = data_dir / "credentials.enc"
        self._secret = secret or os.environ.get("CREDENTIAL_SECRET", "")
        if not self._secret:
            self._secret = self._resolve_or_generate_secret(data_dir)
        # Cache derived key to avoid repeated 100k iteration PBKDF2 (~60ms) overhead
        self._cached_key: bytes | None = None
        self._cached_salt: bytes | None = None

    @staticmethod
    def _resolve_or_generate_secret(data_dir: Path) -> str:
        """Load persisted secret or generate a new one."""
        secret_path = data_dir / ".secret"
        if secret_path.exists():
            return secret_path.read_text().strip()
        data_dir.mkdir(parents=True, exist_ok=True)
        secret = os.urandom(32).hex()
        secret_path.write_text(secret)
        try:
            secret_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass  # Windows may not support chmod
        return secret

    def _derive_key(self, salt: bytes) -> bytes:
        if self._cached_key is not None and self._cached_salt == salt:
            return self._cached_key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=_KDF_ITERATIONS,
        )
        self._cached_key = kdf.derive(self._secret.encode())
        self._cached_salt = salt
        return self._cached_key

    def store(self, credentials: dict[str, str]) -> None:
        """Encrypt and save credentials using a new random salt."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        salt = os.urandom(_SALT_SIZE)
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(_NONCE_SIZE)
        plaintext = json.dumps(credentials).encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # Format: [SALT][salt_bytes][nonce_bytes][ciphertext]
        self._path.write_bytes(_SALT_PREFIX + salt + nonce + ciphertext)
        try:
            self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass  # Windows may not support chmod

    def load(self) -> dict[str, str] | None:
        """Load and decrypt credentials. Returns None if not found."""
        if not self._path.exists():
            return None
        data = self._path.read_bytes()

        # Check for new format with embedded salt
        if data.startswith(_SALT_PREFIX):
            salt_start = len(_SALT_PREFIX)
            nonce_start = salt_start + _SALT_SIZE
            cipher_start = nonce_start + _NONCE_SIZE
            salt = data[salt_start:nonce_start]
            nonce = data[nonce_start:cipher_start]
            ciphertext = data[cipher_start:]
        else:
            # Legacy format
            salt = _LEGACY_SALT
            nonce = data[:_NONCE_SIZE]
            ciphertext = data[_NONCE_SIZE:]

        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext)

    def delete(self) -> None:
        """Delete stored credentials."""
        if self._path.exists():
            self._path.unlink()
