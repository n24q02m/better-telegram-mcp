"""Offline proof that per-sub session state survives a simulated container recreate.

The live recreate verification runs against CF (Task 11.5); this guards the
same invariant in CI using a shared (durable) backend across two provider
instances WHILE rotating the machine-key context (Path.home) to faithfully
model CF's ephemeral on-disk ``.secret`` -- otherwise the index-durability
invariant is not actually exercised (see Step 11.7 prose).
"""

from __future__ import annotations

import pytest
from mcp_core.storage.backends import InMemoryBackend
from mcp_core.storage.string_session_store import StringSessionStore

from better_telegram_mcp.auth.in_memory_session_store import SessionInfo
from better_telegram_mcp.auth.kv_session_store import KvSessionStore
from better_telegram_mcp.auth.telegram_auth_provider import TelegramAuthProvider

pytestmark = pytest.mark.e2e


async def test_session_survives_recreate(monkeypatch, tmp_path):
    monkeypatch.setenv("CREDENTIAL_SECRET", "stable-secret")
    backend = InMemoryBackend()  # stands in for the durable KV namespace

    # --- instance 1: an authed user writes session string + metadata ---
    StringSessionStore("telegram", "subA", backend=backend).save("1AaBb==auth-key")
    KvSessionStore(backend=backend).store(
        "subA", SessionInfo(session_name="subA", mode="user", phone="+1")
    )

    # --- instance 2 (recreate): brand-new provider, SAME durable backend ---
    class _FakeUserBackend:
        def __init__(self, settings, backend=None):
            self._settings = settings
            self._loaded = StringSessionStore(
                "telegram", settings.session_name, backend=backend
            ).load()

        async def connect(self):
            pass

    monkeypatch.setattr(
        "better_telegram_mcp.auth.telegram_auth_provider.UserBackend", _FakeUserBackend
    )
    provider = TelegramAuthProvider(
        tmp_path,
        37984984,
        "hash",
        backend=backend,
        store=KvSessionStore(backend=backend),
    )
    restored = await provider.restore_sessions()

    assert restored == 1, "session metadata must survive recreate"
    rebuilt = provider.resolve_backend("subA")
    assert rebuilt is not None
    assert rebuilt._loaded == "1AaBb==auth-key", (
        "StringSession auth_key must survive recreate"
    )


async def test_index_survives_ephemeral_machine_secret(monkeypatch, tmp_path):
    """THE index-durability guard: the KvSessionStore index must decrypt after a
    container recreate where the on-disk machine ``.secret`` is regenerated.

    This is the assertion the naive single-home-dir test omits. We point
    ``Path.home()`` at a FRESH directory between the write ("instance 1") and the
    read ("instance 2"), so the machine ``.secret`` (per_plugin_store.py:51-60)
    differs across instances exactly as on CF. The index blob must still be
    decryptable -- which holds ONLY because Task 5 keys it under a synthetic
    non-None sub (CREDENTIAL_SECRET path). Under a ``sub=None`` index design the
    index would be machine-.secret-encrypted and ``load_all()`` would return {}
    here, regressing restore to 0 sessions.
    """
    monkeypatch.setenv("CREDENTIAL_SECRET", "stable-secret")
    backend = InMemoryBackend()  # durable KV survives recreate

    # --- instance 1: home dir A; an authed user writes session + index ---
    home_a = tmp_path / "home_a"
    home_a.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home_a)
    KvSessionStore(backend=backend).store(
        "subA", SessionInfo(session_name="subA", mode="user", phone="+1")
    )

    # --- instance 2 (recreate): brand-new home dir B -> NEW machine .secret ---
    home_b = tmp_path / "home_b"
    home_b.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home_b)

    restored = KvSessionStore(backend=backend).load_all()
    assert set(restored) == {"subA"}, (
        "index must decrypt under a NEW machine-key context -- a sub=None index "
        "(machine-.secret-encrypted) would return {} here and regress restore to 0"
    )
    assert restored["subA"].phone == "+1"


async def test_single_user_config_survives_ephemeral_machine_secret(
    monkeypatch, tmp_path
):
    """Same machine-key-rotation guard for the single-user config blob (Task 7).

    The single-user config is keyed under the synthetic non-None sub
    ``shared-single-user`` so it is CREDENTIAL_SECRET-encrypted and survives the
    ephemeral ``.secret``; a ``sub=None`` config would be undecryptable here.
    """
    monkeypatch.setenv("CREDENTIAL_SECRET", "stable-secret")
    monkeypatch.setenv("MCP_STORAGE_BACKEND", "cf-kv")
    backend = InMemoryBackend()

    from better_telegram_mcp.credential_state import (
        _read_single_user_config,
        _write_single_user_config,
    )

    home_a = tmp_path / "home_a"
    home_a.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home_a)
    _write_single_user_config({"TELEGRAM_PHONE": "+10000000000"}, backend=backend)

    home_b = tmp_path / "home_b"
    home_b.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home_b)
    assert _read_single_user_config(backend=backend) == {
        "TELEGRAM_PHONE": "+10000000000"
    }, "single-user config must decrypt under a NEW machine-key context"


async def test_no_cross_sub_bleed(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "stable-secret")
    backend = InMemoryBackend()
    StringSessionStore("telegram", "subA", backend=backend).save("KEY-A")
    StringSessionStore("telegram", "subB", backend=backend).save("KEY-B")
    assert StringSessionStore("telegram", "subA", backend=backend).load() == "KEY-A"
    assert StringSessionStore("telegram", "subB", backend=backend).load() == "KEY-B"
