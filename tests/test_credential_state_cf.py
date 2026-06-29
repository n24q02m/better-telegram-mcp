"""Single-user creds route through the backend seam in CF mode (not machine config.enc)."""

from __future__ import annotations

from mcp_core.storage.backends import InMemoryBackend

from better_telegram_mcp.credential_state import (
    _write_single_user_config,
    read_single_user_config,
)


def test_cf_mode_roundtrip_via_backend(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "k")
    monkeypatch.setenv("MCP_STORAGE_BACKEND", "cf-kv")
    mem = InMemoryBackend()
    cfg = {"TELEGRAM_PHONE": "+10000000000"}
    _write_single_user_config(cfg, backend=mem)
    # Encrypted in the backend under the single-user config key, decryptable back.
    # The blob is keyed under the synthetic non-None sub (shared-single-user) so
    # it is encrypted with CREDENTIAL_SECRET (per_plugin_store.py:98), NOT the
    # on-disk machine .secret -- otherwise it would be undecryptable after a CF
    # recreate.
    assert mem.get("telegram/subs/shared-single-user/config") is not None
    # Sanity: there is NO sub=None blob (which would be machine-.secret-encrypted).
    assert mem.get("telegram/config") is None
    assert read_single_user_config(backend=mem) == cfg


def test_local_default_uses_config_enc(monkeypatch, tmp_path):
    """Without cf-kv the legacy config.enc path is used (machine-bound)."""
    monkeypatch.delenv("MCP_STORAGE_BACKEND", raising=False)
    from mcp_core.storage import config_file

    config_file.set_config_path(str(tmp_path / "config.enc"))
    try:
        _write_single_user_config({"TELEGRAM_PHONE": "+1"})
        assert read_single_user_config() == {"TELEGRAM_PHONE": "+1"}
    finally:
        config_file.set_config_path(None)
        config_file.clear_key_cache_for_testing()
