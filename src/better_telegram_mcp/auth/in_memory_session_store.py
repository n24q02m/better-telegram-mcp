"""In-memory per-user session store (TC-NearZK).

Replaces deprecated per_user_session_store.py (disk-encrypted AES-GCM +
PBKDF2) for HTTP multi-user mode. Aligns with Notion's in-memory
pattern: server has access during request lifetime; restart clears all
sessions, users re-auth via OTP/2FA flow.

Trust model: server admin (n24q02m operator) can dump live memory via
debugger but no persistent file = no FS-dump compromise.

See ~/projects/.superpower/mcp-core/specs/2026-04-30-trust-model-alignment.md
§ 4.D3 + § 5.A8.
"""

from __future__ import annotations

import copy

from .per_user_session_store import SessionInfo


class InMemorySessionStore:
    """Per-user MTProto session store with no disk persistence.

    Drop-in replacement for PerUserSessionStore (same public API).
    Constructor takes no arguments — no data_dir or secret needed.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def store(self, bearer: str, info: SessionInfo) -> None:
        """Store a session for the given bearer token. Overwrites existing."""
        self._store[bearer] = info.to_dict()

    def load(self, bearer: str) -> SessionInfo | None:
        """Load session info for a bearer token. Returns None if not found."""
        data = self._store.get(bearer)
        if data is None:
            return None
        return SessionInfo.from_dict(copy.deepcopy(data))

    def load_all(self) -> dict[str, SessionInfo]:
        """Load all stored sessions."""
        return {
            bearer: SessionInfo.from_dict(copy.deepcopy(data))
            for bearer, data in self._store.items()
        }

    def delete(self, bearer: str) -> bool:
        """Delete a session. Returns True if it existed."""
        if bearer not in self._store:
            return False
        del self._store[bearer]
        return True
