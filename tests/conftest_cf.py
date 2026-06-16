"""Cloudflare-pilot test fixtures for better-telegram-mcp."""

from __future__ import annotations

from urllib.parse import unquote

import pytest


class FakeKvHttp:
    """Injectable http for mcp_core CfKvBackend.

    Implements ``.request(method, url, data, headers) -> (status, body)`` exactly
    as mcp-core's CfKvBackend expects (URL-encoded single-segment key).
    """

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def request(self, method, url, data=None, headers=None):
        key = unquote(url.rsplit("/", 1)[-1])
        if method == "PUT":
            self.store[key] = data or b""
            return (200, b"")
        if method == "GET":
            return (200, self.store[key]) if key in self.store else (404, b"")
        if method == "DELETE":
            existed = key in self.store
            self.store.pop(key, None)
            return (200, b"") if existed else (404, b"")
        raise AssertionError(f"unexpected method {method}")


class FakeStringSessionClient:
    """Stand-in for telethon.TelegramClient that records the session passed in.

    UserBackend.connect() constructs a TelegramClient(session, api_id, api_hash);
    in unit tests we patch TelegramClient with this double so no live MTProto
    socket is opened. It exposes ``.session`` (the SaveOnChangeStringSession),
    ``connect``/``disconnect``/``is_connected``/``is_user_authorized`` so the
    backend's connect path is exercised without the network.
    """

    def __init__(self, session, api_id=None, api_hash=None):
        self.session = session
        self._connected = False
        self._authorized = False

    async def connect(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    def is_connected(self):
        return self._connected

    async def is_user_authorized(self):
        return self._authorized


@pytest.fixture
def fake_kv_http():
    return FakeKvHttp()


@pytest.fixture
def cf_env(monkeypatch, tmp_path):
    """Canonical CF env preset; secrets are dummies (never inline real ones)."""
    monkeypatch.setenv("CREDENTIAL_SECRET", "test-credential-secret")
    monkeypatch.setenv("MCP_STORAGE_BACKEND", "cf-kv")
    monkeypatch.setenv("MCP_KV_BASE_URL", "http://kv.internal")
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("PUBLIC_URL", "https://telegram.n24q02m.com")
    monkeypatch.setenv("MCP_DCR_SERVER_SECRET", "test-dcr-secret")
    monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))


@pytest.fixture
def local_default_env(monkeypatch):
    """Backward-compat: no CF env -> LocalFs + on-disk session."""
    for var in (
        "MCP_STORAGE_BACKEND",
        "MCP_KV_BASE_URL",
        "MCP_TRANSPORT",
        "PUBLIC_URL",
    ):
        monkeypatch.delenv(var, raising=False)
