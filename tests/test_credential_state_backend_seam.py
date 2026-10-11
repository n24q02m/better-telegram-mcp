"""Single-user creds route through an injected credential backend when one is given."""

from __future__ import annotations

from mcp_core.storage.backends import InMemoryBackend

from telegram.credential_state import (
    _delete_single_user_config,
    _read_single_user_config,
    _write_single_user_config,
)


def test_injected_backend_roundtrip(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "k")
    mem = InMemoryBackend()
    cfg = {"TELEGRAM_PHONE": "+10000000000"}
    _write_single_user_config(cfg, backend=mem)
    # Encrypted in the backend under the single-user config key, decryptable back.
    # The blob is keyed under the synthetic non-None sub (shared-single-user) so
    # it is encrypted with CREDENTIAL_SECRET (per_plugin_store.py:98), NOT the
    # on-disk machine .secret.
    assert mem.get("telegram/subs/shared-single-user/config") is not None
    # Sanity: there is NO sub=None blob (which would be machine-.secret-encrypted).
    assert mem.get("telegram/config") is None
    assert _read_single_user_config(backend=mem) == cfg

    _delete_single_user_config(backend=mem)
    assert _read_single_user_config(backend=mem) is None


def test_injected_backend_survives_new_machine_secret(monkeypatch, tmp_path):
    """The injected-backend blob decrypts under a fresh machine-key context."""
    monkeypatch.setenv("CREDENTIAL_SECRET", "stable-secret")
    backend = InMemoryBackend()

    home_a = tmp_path / "home_a"
    home_a.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home_a)
    _write_single_user_config({"TELEGRAM_PHONE": "+10000000000"}, backend=backend)

    home_b = tmp_path / "home_b"
    home_b.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home_b)
    assert _read_single_user_config(backend=backend) == {
        "TELEGRAM_PHONE": "+10000000000"
    }


def test_local_default_uses_per_plugin_store(monkeypatch, tmp_path):
    """Without an injected backend the single-user blob lands in PerPluginStore (sub=None).

    That sub=None machine-key store (``telegram/config`` ->
    ``~/.telegram-mcp/config.json``) is exactly what ``config``/``doctor`` read
    via ``build_cli(plugin_name="telegram")`` -- distinct from the
    injected-backend synthetic-sub blob asserted above.
    """
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    from mcp_core.storage.per_plugin_store import PerPluginStore

    _write_single_user_config({"TELEGRAM_PHONE": "+1"})

    assert PerPluginStore("telegram").load() == {"TELEGRAM_PHONE": "+1"}
    # The local path must NOT use the injected-backend synthetic-sub key.
    assert PerPluginStore("telegram", "shared-single-user").load() is None
    assert _read_single_user_config() == {"TELEGRAM_PHONE": "+1"}
