"""Encrypted per-user session storage for multi-user HTTP mode.

Stores bearer_token -> session_info mappings in a single encrypted file.
Uses AES-256-GCM, key derived from CREDENTIAL_SECRET env var or auto-generated.
Reuses the key derivation pattern from transports/credential_store.py.
"""

from __future__ import annotations

import asyncio
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

_SALT = b"mcp-telegram-sessions"
_KDF_ITERATIONS = 100_000
_NONCE_SIZE = 12


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
        self._cached_key: bytes | None = None

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
            secret_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass  # Windows may not support chmod
        return secret

    def _derive_key(self) -> bytes:
        if self._cached_key is not None:
            return self._cached_key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_SALT,
            iterations=_KDF_ITERATIONS,
        )
        self._cached_key = kdf.derive(self._secret.encode())
        return self._cached_key

    def _encrypt(self, data: bytes) -> bytes:
        key = self._derive_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def _decrypt(self, data: bytes) -> bytes:
        key = self._derive_key()
        nonce, ciphertext = data[:_NONCE_SIZE], data[_NONCE_SIZE:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def _read_all_sync(self) -> dict[str, dict]:
        """Synchronous version of read_all for thread offloading."""
        if not self._path.exists():
            return {}
        raw = self._path.read_bytes()
        plaintext = self._decrypt(raw)
        return json.loads(plaintext)

    def _write_all_sync(self, sessions: dict[str, dict]) -> None:
        """Synchronous version of write_all for thread offloading."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        plaintext = json.dumps(sessions).encode()
        encrypted = self._encrypt(plaintext)
        self._path.write_bytes(encrypted)
        try:
            self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    async def store(self, bearer: str, info: SessionInfo) -> None:
        """Store a session for the given bearer token."""
        sessions = await asyncio.to_thread(self._read_all_sync)
        sessions[bearer] = info.to_dict()
        await asyncio.to_thread(self._write_all_sync, sessions)

    async def load(self, bearer: str) -> SessionInfo | None:
        """Load session info for a bearer token. Returns None if not found."""
        sessions = await asyncio.to_thread(self._read_all_sync)
        data = sessions.get(bearer)
        if data is None:
            return None
        return SessionInfo.from_dict(data)

    async def load_all(self) -> dict[str, SessionInfo]:
        """Load all stored sessions."""
        sessions = await asyncio.to_thread(self._read_all_sync)
        return {
            bearer: SessionInfo.from_dict(data) for bearer, data in sessions.items()
        }

    async def delete(self, bearer: str) -> bool:
        """Delete a session. Returns True if it existed."""
        sessions = await asyncio.to_thread(self._read_all_sync)
        if bearer not in sessions:
            return False
        del sessions[bearer]
        await asyncio.to_thread(self._write_all_sync, sessions)
        return True
