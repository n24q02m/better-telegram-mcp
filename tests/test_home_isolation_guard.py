"""Guard: the autouse ``_isolate_per_plugin_home`` fixture must stay in place.

The fixture in conftest.py is defense-in-depth -- no test leaks into the real
home today. These tests exist so that if someone deletes the fixture, the
suite goes red immediately instead of silently starting to write into the
developer's (or the CI runner's) real ~/.telegram-mcp/.

``test_single_user_write_stays_out_of_the_real_store`` is the load-bearing
one. It drives the production path that can genuinely write there:
``credential_state._write_single_user_config`` -> ``PerPluginStore("telegram")``
with ``sub=None`` -> ``backend_from_env()`` -> ``LocalFsBackend`` ->
``~/.telegram-mcp/config.json`` plus the ``.secret`` machine key. Today every
test of that surface opts into the local ``isolated_home`` fixture by hand; a
new one that forgets would hit the real directory.

Note the asserts compare against the real *store* directory, not the real
home. On Windows pytest's tmp_path lives under ``~\\AppData\\Local\\Temp``,
so "is not under the real home" is false for a correctly isolated path.
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp_core.storage.per_plugin_store import PerPluginStore

from better_telegram_mcp.credential_state import _write_single_user_config

# Captured at import time: collection runs before any fixture, so this is the
# genuine home directory, whatever the fixture later redirects Path.home() to.
_REAL_HOME = Path(os.path.expanduser("~")).resolve()
_REAL_STORE_DIR = _REAL_HOME / ".telegram-mcp"


def _snapshot(directory: Path) -> set[tuple[str, int, int]]:
    """Identify every file under directory by path, size and mtime.

    Works whether or not the directory exists, so this never assumes the
    developer has no real ~/.telegram-mcp/ of their own.
    """
    if not directory.exists():
        return set()
    return {
        (str(path), path.stat().st_size, path.stat().st_mtime_ns)
        for path in directory.rglob("*")
        if path.is_file()
    }


def test_home_is_redirected_away_from_the_real_home():
    assert Path.home().resolve() != _REAL_HOME


def test_per_plugin_store_path_is_not_in_the_real_store_dir():
    cred_path = PerPluginStore(plugin_name="telegram").cred_path.resolve()
    assert _REAL_STORE_DIR != cred_path
    assert _REAL_STORE_DIR not in cred_path.parents


def test_single_user_write_stays_out_of_the_real_store(monkeypatch):
    """Drive the production write path that can reach the real home."""
    monkeypatch.delenv("MCP_STORAGE_BACKEND", raising=False)
    before = _snapshot(_REAL_STORE_DIR)

    _write_single_user_config({"TELEGRAM_BOT_TOKEN": "guard-token"})

    written = sorted(Path.home().glob(".telegram-mcp/*"))
    assert written, "expected the LocalFsBackend write to land in the tmp home"
    for path in written:
        assert _REAL_STORE_DIR not in path.resolve().parents
    assert _snapshot(_REAL_STORE_DIR) == before
