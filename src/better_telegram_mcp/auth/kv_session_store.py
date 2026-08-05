"""Durable per-sub session metadata store backed by mcp-core PerPluginStore.

Uses a CF KV (or InMemoryBackend in tests) via PerPluginStore for encrypted
per-sub storage.  The index (list of known subs) is stored under a synthetic
non-None sub (_INDEX_SUB = "shared-index") so that PerPluginStore._key() takes
the CREDENTIAL_SECRET / PBKDF2 path — not the machine-secret-file path which
is ephemeral on Cloudflare containers.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from mcp_core.storage.per_plugin_store import PerPluginStore

from .in_memory_session_store import SessionInfo

if TYPE_CHECKING:
    from mcp_core.storage.backends import CredentialBackend


_PLUGIN = "telegram"
_META_LEAF = "session_meta"
_INDEX_LEAF = "session_index"
# CRITICAL: must be a non-None string so PerPluginStore._key() uses
# CREDENTIAL_SECRET (PBKDF2) instead of an ephemeral machine-secret file.
_INDEX_SUB = "shared-index"


class KvSessionStore:
    """Per-user MTProto session store backed by an mcp-core CredentialBackend.

    Drop-in replacement for InMemorySessionStore — same public API:
    store / load / load_all / delete.  On CF the backend is CfKvBackend;
    in unit tests pass InMemoryBackend.
    """

    def __init__(self, backend: CredentialBackend | None = None) -> None:
        self._backend = backend  # None → PerPluginStore calls backend_from_env()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sub_store(self, sub: str) -> PerPluginStore:
        return PerPluginStore(
            plugin_name=_PLUGIN,
            sub=sub,
            backend=self._backend,
            sub_key=_META_LEAF,
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
    # Public API (mirrors InMemorySessionStore)
    # ------------------------------------------------------------------

    def store(self, bearer: str, info: SessionInfo) -> None:
        """Persist encrypted session info for bearer. Updates index."""
        self._sub_store(bearer).save(info.to_dict())

        subs = self._load_index()
        if bearer not in subs:
            subs.append(bearer)
            self._save_index(subs)

    def load(self, bearer: str) -> SessionInfo | None:
        """Load session info for bearer. Returns None if not found."""
        data = self._sub_store(bearer).load()
        if data is None:
            return None
        return SessionInfo.from_dict(data)

    def load_all(self) -> dict[str, SessionInfo]:
        """Load all stored sessions from the index.

        Optimized to parallelize individual `load()` calls across all session subjects.
        This resolves an N+1 query bottleneck and overlaps KV store I/O and
        heavy PBKDF2 key derivations, as cryptography releases the GIL.
        """
        subs = self._load_index()
        result: dict[str, SessionInfo] = {}

        with ThreadPoolExecutor() as executor:
            infos = executor.map(self.load, subs)

        for sub, info in zip(subs, infos, strict=True):
            if info is not None:
                result[sub] = info

        return result

    def has_any(self) -> bool:
        """Check if any sessions exist without doing N+1 loads."""
        return bool(self._load_index())

    def delete(self, bearer: str) -> bool:
        """Delete session for bearer. Returns True if it existed."""
        existing = self.load(bearer)
        if existing is None:
            return False
        self._sub_store(bearer).clear()
        subs = self._load_index()
        subs = [s for s in subs if s != bearer]
        self._save_index(subs)
        return True
