"""Regression tests for MCP Registry server metadata."""

import json
from pathlib import Path

MCP_REGISTRY_MAX_DESCRIPTION_LENGTH = 100
SERVER_MANIFEST = Path(__file__).resolve().parents[1] / "server.json"


def test_server_description_respects_mcp_registry_limit() -> None:
    """The published manifest must satisfy the registry's 100-character limit."""
    manifest = json.loads(SERVER_MANIFEST.read_text(encoding="utf-8"))
    description = manifest["description"]

    assert isinstance(description, str)
    assert 0 < len(description) <= MCP_REGISTRY_MAX_DESCRIPTION_LENGTH
