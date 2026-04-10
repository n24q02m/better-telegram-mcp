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


class CredentialStore:
    """Server-side encrypted credential storage.

    Used in HTTP transport mode to persist Telegram credentials
    received via the relay page.
    """

    _salt_cache: dict[Path, bytes] = {}
    _secret_cache: dict[Path, str] = {}

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
        resolved_path = self._salt_path.resolve()
        if self._salt_path.exists():
            if resolved_path in self._salt_cache:
                return self._salt_cache[resolved_path]
            salt = self._salt_path.read_bytes()
            self._salt_cache[resolved_path] = salt
            return salt

        # If .salt disappeared, invalidate cache for this path
        self._salt_cache.pop(resolved_path, None)

        # Backward compatibility: existing credentials use legacy hardcoded salt
        if self._path.exists():
            return _LEGACY_SALT

        # New installation: generate random salt
        salt = os.urandom(16)
        self._salt_path.parent.mkdir(parents=True, exist_ok=True)
        self._salt_path.write_bytes(salt)
        self._salt_cache[resolved_path] = salt
        try:
            self._salt_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass
        return salt

    @classmethod
    def _resolve_or_generate_secret(cls, data_dir: Path) -> str:
        """Load persisted secret or generate a new one."""
        secret_path = data_dir / ".secret"
        resolved_path = secret_path.resolve()
        if secret_path.exists():
            if resolved_path in cls._secret_cache:
                return cls._secret_cache[resolved_path]
            secret = secret_path.read_text().strip()
            cls._secret_cache[resolved_path] = secret
            return secret

        # If .secret disappeared, invalidate cache for this path
        cls._secret_cache.pop(resolved_path, None)

        data_dir.mkdir(parents=True, exist_ok=True)
        secret = os.urandom(32).hex()
        secret_path.write_text(secret)
        cls._secret_cache[resolved_path] = secret
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

    def store(self, credentials: dict[str, str]) -> None:
        """Encrypt and save credentials."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Migrate from legacy hardcoded salt to random salt on re-encryption
        if self._salt == _LEGACY_SALT:
            new_salt = os.urandom(16)
            self._salt_path.write_bytes(new_salt)
            self._salt_cache[self._salt_path.resolve()] = new_salt
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
        self._cached_credentials = copy.deepcopy(credentials)
        self._path.write_bytes(nonce + ciphertext)
        try:
            self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass  # Windows may not support chmod

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
