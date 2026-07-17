"""Single-user credential storage unification (config-status parity).

Regression coverage for the ``config status`` / ``doctor`` mismatch: the
server used to persist single-user credentials to the legacy shared
``config.enc`` (keyed by the console name ``better-telegram-mcp``) while
``mcp_core.build_cli``'s built-ins read ``PerPluginStore`` (keyed by the
plugin slug ``telegram``), so a saved credential was reported as "not
configured".

These tests exercise the real ``PerPluginStore`` + legacy ``config_file``
backends against an isolated ``$HOME`` (no mocks on the storage layer) so a
genuine path/slug mismatch would fail them. The contract mirrored here is the
storage-unify cutover (mcp-core #668):

    WRITE  -> PerPluginStore("telegram").save(config)
    READ   -> PerPluginStore("telegram").load() ?? legacy read_config(SERVER_NAME)
    DELETE -> PerPluginStore("telegram").clear() + legacy delete_config(SERVER_NAME)
"""

from __future__ import annotations

import sys

import pytest

from better_telegram_mcp.credential_state import (
    SERVER_NAME,
    _delete_single_user_config,
    _read_single_user_config,
    _write_single_user_config,
    resolve_credential_state,
)

# The credential storage slug the server writes under and build_cli reads from.
PLUGIN = "telegram"


def _per_plugin_store():
    from mcp_core.storage.per_plugin_store import PerPluginStore

    return PerPluginStore(PLUGIN)


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Point every credential store at a throwaway home + config path."""
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MCP_STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_PHONE", raising=False)

    from mcp_core.storage import config_file

    config_file.set_config_path(str(tmp_path / "mcp" / "config.enc"))
    config_file.clear_key_cache_for_testing()
    yield tmp_path
    config_file.set_config_path(None)
    config_file.clear_key_cache_for_testing()


def test_write_routes_to_per_plugin_store(isolated_home):
    """A single-user save lands in the store ``config status`` reads."""
    _write_single_user_config({"TELEGRAM_BOT_TOKEN": "123:abc"})

    assert _per_plugin_store().load() == {"TELEGRAM_BOT_TOKEN": "123:abc"}


def test_read_round_trips_through_per_plugin_store(isolated_home):
    _write_single_user_config({"TELEGRAM_PHONE": "+84900000000"})

    assert _read_single_user_config() == {"TELEGRAM_PHONE": "+84900000000"}


def test_read_falls_back_to_legacy_config(isolated_home):
    """Credentials written before the cutover stay readable (zero re-auth)."""
    from mcp_core.storage import config_file

    config_file.write_config(SERVER_NAME, {"TELEGRAM_PHONE": "+84900000000"})
    # Nothing in the per-plugin store yet -- the read must reach the legacy blob.
    assert _per_plugin_store().load() is None

    assert _read_single_user_config() == {"TELEGRAM_PHONE": "+84900000000"}


def test_read_prefers_per_plugin_store_over_legacy(isolated_home):
    """When both stores hold a value the per-plugin store wins."""
    from mcp_core.storage import config_file

    config_file.write_config(SERVER_NAME, {"TELEGRAM_PHONE": "legacy"})
    _write_single_user_config({"TELEGRAM_BOT_TOKEN": "new:token"})

    assert _read_single_user_config() == {"TELEGRAM_BOT_TOKEN": "new:token"}


def test_write_migrates_legacy_on_next_save(isolated_home):
    """A save after an upgrade supersedes the legacy blob in the new store."""
    from mcp_core.storage import config_file

    config_file.write_config(SERVER_NAME, {"TELEGRAM_PHONE": "legacy"})
    _write_single_user_config({"TELEGRAM_BOT_TOKEN": "migrated:token"})

    assert _per_plugin_store().load() == {"TELEGRAM_BOT_TOKEN": "migrated:token"}


def test_delete_clears_both_stores(isolated_home):
    """Logout / reset must leave nothing behind in either store."""
    from mcp_core.storage import config_file

    config_file.write_config(SERVER_NAME, {"TELEGRAM_PHONE": "legacy"})
    _write_single_user_config({"TELEGRAM_BOT_TOKEN": "123:abc"})

    _delete_single_user_config()

    assert _per_plugin_store().load() is None
    assert config_file.read_config(SERVER_NAME) is None


def test_legacy_only_install_still_resolves_configured(isolated_home):
    """Zero-data-loss: an existing legacy-only install boots as CONFIGURED."""
    from mcp_core.storage import config_file

    from better_telegram_mcp.credential_state import CredentialState

    config_file.write_config(SERVER_NAME, {"TELEGRAM_BOT_TOKEN": "legacy:token"})

    assert resolve_credential_state() == CredentialState.CONFIGURED


def test_config_status_reports_configured_after_save(isolated_home, capsys):
    """End-to-end: `better-telegram-mcp config status` finds a saved credential."""
    from better_telegram_mcp import cli

    _write_single_user_config({"TELEGRAM_BOT_TOKEN": "123:abc"})

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", ["better-telegram-mcp", "config", "status"])
        rc = cli.main()

    out = capsys.readouterr().out
    assert rc == 0
    assert "not configured" not in out
    assert "configured" in out
