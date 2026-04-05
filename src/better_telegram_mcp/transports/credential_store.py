"""Encrypted credential storage for HTTP mode.

Credentials stored at: DATA_DIR/credentials.enc
Key derived from server secret (CREDENTIAL_SECRET env var or auto-generated).
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_MAGIC = b"SALT"
_LEGACY_SALT = b"mcp-telegram-creds"
_KDF_ITERATIONS = 100_000
_NONCE_SIZE = 12


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
        # Cache derived key to avoid repeated 100k iteration PBKDF2 (~60ms) overhead
        self._cached_key: tuple[bytes, bytes] | None = None  # (salt, key)

    def _resolve_legacy_salt(self) -> bytes:
        """Load persisted salt or fallback to legacy."""
        if self._salt_path.exists():
            return self._salt_path.read_bytes()
        return _LEGACY_SALT

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
        if self._cached_key and self._cached_key[0] == salt:
            return self._cached_key[1]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=_KDF_ITERATIONS,
        )
        key = kdf.derive(self._secret.encode())
        self._cached_key = (salt, key)
        return key

    def store(self, credentials: dict[str, str]) -> None:
        """Encrypt and save credentials using a new random salt."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        salt = os.urandom(16)
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(_NONCE_SIZE)
        plaintext = json.dumps(credentials).encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Embedded format: MAGIC + SALT + NONCE + CIPHERTEXT
        self._path.write_bytes(_MAGIC + salt + nonce + ciphertext)

        try:
            self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass

        # Cleanup legacy salt file if it exists
        if self._salt_path.exists():
            try:
                self._salt_path.unlink()
            except OSError:
                pass

    def load(self) -> dict[str, str] | None:
        """Load and decrypt credentials. Supports legacy and embedded salt formats."""
        if not self._path.exists():
            return None

        data = self._path.read_bytes()

        if data.startswith(_MAGIC):
            # Embedded salt format
            salt = data[len(_MAGIC) : len(_MAGIC) + 16]
            nonce_start = len(_MAGIC) + 16
            nonce = data[nonce_start : nonce_start + _NONCE_SIZE]
            ciphertext = data[nonce_start + _NONCE_SIZE :]
            key = self._derive_key(salt)
        else:
            # Legacy format
            salt = self._resolve_legacy_salt()
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
