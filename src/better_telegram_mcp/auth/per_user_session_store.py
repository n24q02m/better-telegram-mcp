"""Encrypted per-user session storage for multi-user HTTP mode.

Stores bearer_token -> session_info mappings in a single encrypted file.
Uses AES-256-GCM, key derived from CREDENTIAL_SECRET env var or auto-generated.
Reuses the key derivation pattern from transports/credential_store.py.
"""

from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_LEGACY_SALT = b"mcp-telegram-sessions"
_KDF_ITERATIONS = 100_000
_NONCE_SIZE = 12
_SALT_SIZE = 16
_SALT_PREFIX = b"SALT"


@dataclass
class SessionInfo:
    """Per-user session metadata."""

    session_name: str
    mode: Literal["bot", "user"]
    api_id: int | None = None
    api_hash: str | None = None
    phone: str | None = None
    bot_token: str | None = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SessionInfo:
        return cls(**data)


class PerUserSessionStore:
    """Encrypted storage for per-user Telegram sessions.

    All sessions stored in a single encrypted file at data_dir/sessions.enc.
    Maps bearer_token (hashed) -> SessionInfo.
    """

    def __init__(self, data_dir: Path, secret: str | None = None) -> None:
        self._path = data_dir / "sessions.enc"
        self._secret = secret or os.environ.get("CREDENTIAL_SECRET", "")
        if not self._secret:
            self._secret = self._resolve_or_generate_secret(data_dir)
        # Cache derived key to avoid repeated 100k iteration PBKDF2 overhead
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

    def _encrypt(self, data: bytes) -> bytes:
        salt = os.urandom(_SALT_SIZE)
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        # Format: [SALT][salt_bytes][nonce_bytes][ciphertext]
        return _SALT_PREFIX + salt + nonce + ciphertext

    def _decrypt(self, data: bytes) -> bytes:
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
        return aesgcm.decrypt(nonce, ciphertext, None)

    def _read_all(self) -> dict[str, dict]:
        """Read and decrypt all sessions from disk."""
        if not self._path.exists():
            return {}
        raw = self._path.read_bytes()
        plaintext = self._decrypt(raw)
        return json.loads(plaintext)

    def _write_all(self, sessions: dict[str, dict]) -> None:
        """Encrypt and write all sessions to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        plaintext = json.dumps(sessions).encode()
        encrypted = self._encrypt(plaintext)
        self._path.write_bytes(encrypted)
        try:
            self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass

    def store(self, bearer: str, info: SessionInfo) -> None:
        """Store a session for the given bearer token."""
        sessions = self._read_all()
        sessions[bearer] = info.to_dict()
        self._write_all(sessions)

    def load(self, bearer: str) -> SessionInfo | None:
        """Load session info for a bearer token. Returns None if not found."""
        sessions = self._read_all()
        data = sessions.get(bearer)
        if data is None:
            return None
        return SessionInfo.from_dict(data)

    def load_all(self) -> dict[str, SessionInfo]:
        """Load all stored sessions."""
        sessions = self._read_all()
        return {
            bearer: SessionInfo.from_dict(data) for bearer, data in sessions.items()
        }

    def delete(self, bearer: str) -> bool:
        """Delete a session. Returns True if it existed."""
        sessions = self._read_all()
        if bearer not in sessions:
            return False
        del sessions[bearer]
        self._write_all(sessions)
        return True
