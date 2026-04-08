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

_LEGACY_SALT = b"mcp-telegram-creds"
_KDF_ITERATIONS = 100_000
_NONCE_SIZE = 12


class CredentialStore:
    """Server-side encrypted credential storage.

    Used in HTTP transport mode to persist Telegram credentials
    received via the relay page.
    """

    def __init__(self, data_dir: Path, secret: str | None = None) -> None:
        import threading

        self._path = data_dir / "credentials.enc"
        self._salt_path = data_dir / ".salt"
        self._secret = secret or os.environ.get("CREDENTIAL_SECRET", "")
        if not self._secret:
            self._secret = self._resolve_or_generate_secret(data_dir)
        self._salt = self._resolve_salt()
        # Cache derived key to avoid repeated 100k iteration PBKDF2 (~60ms) overhead
        self._cached_key: bytes | None = None
        self._lock = threading.Lock()

    def _resolve_salt(self) -> bytes:
        """Load persisted salt, fallback to legacy, or generate new one."""
        if self._salt_path.exists():
            return self._salt_path.read_bytes()

        # Backward compatibility: existing credentials use legacy hardcoded salt
        if self._path.exists():
            return _LEGACY_SALT

        # New installation: generate random salt
        salt = os.urandom(16)
        self._salt_path.parent.mkdir(parents=True, exist_ok=True)
        self._salt_path.write_bytes(salt)
        try:
            self._salt_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass
        return salt

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

    def _sync_store(self, credentials: dict[str, str]) -> None:
        """Synchronous implementation of store."""
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)

            # Migrate from legacy hardcoded salt to random salt on re-encryption
            if self._salt == _LEGACY_SALT:
                new_salt = os.urandom(16)
                self._salt_path.write_bytes(new_salt)
                try:
                    self._salt_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
                except OSError:
                    pass
                self._salt = new_salt
                self._cached_key = None  # Force re-derivation

            key = self._derive_key()
            aesgcm = AESGCM(key)
            nonce = os.urandom(_NONCE_SIZE)
            plaintext = json.dumps(credentials).encode()
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
            self._path.write_bytes(nonce + ciphertext)
            try:
                self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
            except OSError:
                pass  # Windows may not support chmod

    async def store(self, credentials: dict[str, str]) -> None:
        """Encrypt and save credentials."""
        import asyncio

        await asyncio.to_thread(self._sync_store, credentials)

    def _sync_load(self) -> dict[str, str] | None:
        """Synchronous implementation of load."""
        with self._lock:
            if not self._path.exists():
                return None
            key = self._derive_key()
            data = self._path.read_bytes()
            nonce, ciphertext = data[:_NONCE_SIZE], data[_NONCE_SIZE:]
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(plaintext)

    async def load(self) -> dict[str, str] | None:
        """Load and decrypt credentials. Returns None if not found."""
        import asyncio

        return await asyncio.to_thread(self._sync_load)

    def _sync_delete(self) -> None:
        """Synchronous implementation of delete."""
        with self._lock:
            if self._path.exists():
                self._path.unlink()

    async def delete(self) -> None:
        """Delete stored credentials."""
        import asyncio

        await asyncio.to_thread(self._sync_delete)
