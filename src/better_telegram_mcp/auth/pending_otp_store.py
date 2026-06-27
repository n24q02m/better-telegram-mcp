"""Durable per-sub pending OTP metadata store backed by mcp-core PerPluginStore.

Uses CF KV (or InMemoryBackend in tests) via PerPluginStore so pending OTP
state survives container sleep/recreate during an in-flight OTP flow.

Each sub stores at key ``telegram/subs/<sub>/pending_otp`` a dict mapping
``bearer -> {phone, phone_code_hash, session_name, created_at}``.
An index under the synthetic ``shared-index`` sub tracks which subs have
pending entries so ``cleanup_expired()`` can purge stale KV entries without
a full key-space scan.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from mcp_core.storage.per_plugin_store import PerPluginStore

if TYPE_CHECKING:
    from mcp_core.storage.backends import CredentialBackend

_PLUGIN = "telegram"
_OTP_LEAF = "pending_otp"
_INDEX_LEAF = "pending_otp_index"
# Must be a non-None string so PerPluginStore._key() uses CREDENTIAL_SECRET
# (PBKDF2) instead of an ephemeral machine-secret file.
_INDEX_SUB = "shared-index"
_OTP_TTL = 300  # 5 minutes


class PendingOtpStore:
    """Durable per-sub pending OTP metadata store.

    Survives container sleep/recreate via CF KV (or InMemoryBackend in tests).
    The pending OTP metadata — phone, phone_code_hash, session_name — is
    persisted so ``complete_user_auth()`` can resume after a container restart.

    NOT persisted: the live Telethon ``backend`` client (cannot be serialized).
    After a restart, ``complete_user_auth()`` falls back to KV to find the
    metadata and re-creates a fresh UserBackend from it.
    """

    def __init__(self, backend: CredentialBackend | None = None) -> None:
        self._backend = backend

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sub_store(self, sub: str) -> PerPluginStore:
        return PerPluginStore(
            plugin_name=_PLUGIN,
            sub=sub,
            backend=self._backend,
            sub_key=_OTP_LEAF,
        )

    def _index_store(self) -> PerPluginStore:
        return PerPluginStore(
            plugin_name=_PLUGIN,
            sub=_INDEX_SUB,
            backend=self._backend,
            sub_key=_INDEX_LEAF,
        )

    def _load_index(self) -> list[str]:
        data = self._index_store().load()
        if not isinstance(data, dict):
            return []
        return list(data.get("subs", []))

    def _save_index(self, subs: list[str]) -> None:
        self._index_store().save({"subs": subs})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_pending_otp(self, sub: str, bearer: str, data: dict) -> None:
        """Persist pending OTP metadata for a bearer under the given sub.

        ``data`` must contain: ``phone``, ``phone_code_hash``, ``session_name``.
        ``created_at`` is auto-populated if missing.
        """
        store = self._sub_store(sub)
        existing = store.load() or {}
        existing[bearer] = {
            "phone": data["phone"],
            "phone_code_hash": data["phone_code_hash"],
            "session_name": data["session_name"],
            "created_at": data.get("created_at", time.time()),
        }
        store.save(existing)

        # Update index
        subs = self._load_index()
        if sub not in subs:
            subs.append(sub)
            self._save_index(subs)

    def load_pending_otp(self, sub: str, bearer: str) -> dict | None:
        """Load pending OTP metadata. Returns None if not found or expired.

        Auto-purges expired entries on load (TTL = 5 min).
        """
        store = self._sub_store(sub)
        existing = store.load()
        if not isinstance(existing, dict) or bearer not in existing:
            return None
        entry = existing[bearer]
        if not isinstance(entry, dict):
            return None
        # TTL check: purge expired entries on access
        if time.time() - entry.get("created_at", 0) > _OTP_TTL:
            del existing[bearer]
            if existing:
                store.save(existing)
            else:
                store.clear()
                self._remove_from_index(sub)
            return None
        return entry

    def delete_pending_otp(self, sub: str, bearer: str) -> bool:
        """Delete pending OTP for bearer. Returns True if it existed."""
        store = self._sub_store(sub)
        existing = store.load()
        if not isinstance(existing, dict) or bearer not in existing:
            return False
        del existing[bearer]
        if existing:
            store.save(existing)
        else:
            store.clear()
            self._remove_from_index(sub)
        return True

    def _remove_from_index(self, sub: str) -> None:
        subs = self._load_index()
        subs = [s for s in subs if s != sub]
        self._save_index(subs)

    def cleanup_expired(self) -> int:
        """Remove expired pending OTP entries from KV. Returns count removed."""
        subs = self._load_index()
        removed = 0
        for sub in list(subs):
            store = self._sub_store(sub)
            existing = store.load()
            if not isinstance(existing, dict) or not existing:
                self._remove_from_index(sub)
                continue
            stale_bearers = []
            now = time.time()
            for bearer, entry in existing.items():
                if (
                    isinstance(entry, dict)
                    and now - entry.get("created_at", 0) > _OTP_TTL
                ):
                    stale_bearers.append(bearer)
            for bearer in stale_bearers:
                del existing[bearer]
                removed += 1
            if existing:
                store.save(existing)
            else:
                store.clear()
                self._remove_from_index(sub)
        return removed
