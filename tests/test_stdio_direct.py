"""Verify the intentional stdio credential gate before MCP startup.

Spawns ``python -m better_telegram_mcp`` with ``MCP_TRANSPORT=stdio`` and
asserts that missing credentials produce a bounded nonzero exit, no MCP
response on stdout, and the documented local auth guidance. The gate runs
before FastMCP initializes, so handshake and ``tools/list`` expectations
without credentials would be invalid.

Marked ``live`` because it spawns a real subprocess and sends a real MCP
initialize request; excluded from the default ``pytest`` invocation but runs
under ``uv run pytest -m live``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.live, pytest.mark.timeout(60)]


def _stdio_env_without_credentials(tmp_path: Path) -> dict[str, str]:
    """Build an isolated environment without Telegram or saved credentials."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
    for key in (
        "MCP_STORAGE_BACKEND",
        "CREDENTIAL_SECRET",
        "MCP_DCR_SERVER_SECRET",
        "DCR_SERVER_SECRET",
        "MASTER_SECRET",
    ):
        env.pop(key, None)

    env.update(
        {
            "MCP_TRANSPORT": "stdio",
            "HOME": str(tmp_path),
            "USERPROFILE": str(tmp_path),
            "APPDATA": str(tmp_path / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(tmp_path / "AppData" / "Local"),
            "XDG_CONFIG_HOME": str(tmp_path / ".config"),
        }
    )
    return env


def _run_stdio_without_credentials(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run stdio with an initialize request but no credential input."""
    args = [sys.executable, "-m", "better_telegram_mcp"]
    stdout_path = tmp_path / "stdio-stdout.txt"
    stderr_path = tmp_path / "stdio-stderr.txt"
    with (
        stdout_path.open("w", encoding="utf-8") as stdout,
        stderr_path.open("w", encoding="utf-8") as stderr,
    ):
        result = subprocess.run(
            args,
            env=_stdio_env_without_credentials(tmp_path),
            input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n',
            stdout=stdout,
            stderr=stderr,
            text=True,
            timeout=10,
            check=False,
        )
    return subprocess.CompletedProcess(
        args,
        result.returncode,
        stdout_path.read_text(encoding="utf-8"),
        stderr_path.read_text(encoding="utf-8"),
    )


def test_stdio_credential_gate_exits_before_mcp_handshake(tmp_path: Path) -> None:
    """Missing stdio credentials stop startup before MCP can respond."""
    result = _run_stdio_without_credentials(tmp_path)
    assert result.returncode != 0
    assert result.stdout.strip() == ""

    stderr = result.stderr
    assert (
        "[better-telegram-mcp] No Telegram credentials configured for stdio mode."
        in stderr
    )
    assert "better-telegram-mcp auth --bot-token <token>" in stderr
    assert "better-telegram-mcp auth --phone <+number>" in stderr
    assert "login is a deprecated alias of auth" in stderr
    assert (
        "Documentation: https://mcp.n24q02m.com/servers/better-telegram-mcp/setup/"
        in stderr
    )
