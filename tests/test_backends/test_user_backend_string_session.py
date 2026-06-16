"""UserBackend uses a KV-backed StringSession in CF mode (no on-disk .session)."""

from __future__ import annotations

from mcp_core.storage.backends import InMemoryBackend
from mcp_core.storage.string_session_store import SaveOnChangeStringSession

from better_telegram_mcp.backends.user_backend import UserBackend
from better_telegram_mcp.config import Settings
from tests.conftest_cf import FakeStringSessionClient


def _settings(tmp_path) -> Settings:
    return Settings(
        api_id=37984984,
        api_hash="2f5f4c76c4de7c07302380c788390100",
        phone="+10000000000",
        session_name="deadbeefdeadbeef",
        data_dir=tmp_path,
    )


async def test_connect_uses_string_session_from_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret")
    captured = {}

    def _fake_client(session, *a, **kw):
        captured["session"] = session
        return FakeStringSessionClient(session)

    monkeypatch.setattr(
        "better_telegram_mcp.backends.user_backend.TelegramClient", _fake_client
    )
    backend = UserBackend(_settings(tmp_path), backend=InMemoryBackend())
    await backend.connect()
    # In CF mode the client is constructed with a SaveOnChangeStringSession,
    # NOT a filesystem path string.
    assert isinstance(captured["session"], SaveOnChangeStringSession)
    # No .session file was created on disk.
    assert not list(tmp_path.glob("*.session"))


async def test_save_on_change_flushes_to_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret")
    mem = InMemoryBackend()

    def _fake_client(session, *a, **kw):
        return FakeStringSessionClient(session)

    monkeypatch.setattr(
        "better_telegram_mcp.backends.user_backend.TelegramClient", _fake_client
    )
    backend = UserBackend(_settings(tmp_path), backend=mem)
    await backend.connect()
    # Simulate a Telethon-internal rewrite (DC migration / key rotation).
    backend._client.session.save()
    assert mem.get("telegram/subs/deadbeefdeadbeef/session") is not None


async def test_empty_backend_starts_unauthorized(monkeypatch, tmp_path):
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-secret")

    def _fake_client(session, *a, **kw):
        return FakeStringSessionClient(session)

    monkeypatch.setattr(
        "better_telegram_mcp.backends.user_backend.TelegramClient", _fake_client
    )
    backend = UserBackend(_settings(tmp_path), backend=InMemoryBackend())
    await backend.connect()
    assert await backend.is_authorized() is False
