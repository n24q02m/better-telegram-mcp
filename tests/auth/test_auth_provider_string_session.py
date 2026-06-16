"""TelegramAuthProvider passes its backend into per-sub UserBackends."""

from __future__ import annotations

from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.auth.in_memory_session_store import SessionInfo
from better_telegram_mcp.auth.telegram_auth_provider import TelegramAuthProvider


async def test_provider_injects_backend_into_user_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret")
    mem = InMemoryBackend()

    captured = {}

    class _FakeUserBackend:
        def __init__(self, settings, backend=None):
            captured["backend"] = backend
            self._settings = settings

        async def connect(self):
            pass

    monkeypatch.setattr(
        "better_telegram_mcp.auth.telegram_auth_provider.UserBackend", _FakeUserBackend
    )
    provider = TelegramAuthProvider(tmp_path, 37984984, "hash", backend=mem)
    info = SessionInfo(session_name="abc123", mode="user", phone="+1")
    await provider._create_backend(info)
    assert captured["backend"] is mem
