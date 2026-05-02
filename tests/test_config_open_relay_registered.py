"""Smoke test: `config__open_relay` MCP tool is registered.

Transparent Bridge v2 / Wave 3 — every MCP server must register the
``config__open_relay`` tool from `mcp_core.relay.tool_helpers` so the LLM
can re-trigger the relay form via tool call.
"""

from __future__ import annotations

from better_telegram_mcp.server import mcp


def test_config_open_relay_tool_registered():
    """`config__open_relay` is present in the FastMCP tool registry."""
    tools = mcp._tool_manager._tools
    assert "config__open_relay" in tools, (
        "config__open_relay tool not registered. Stdio-pure architecture "
        "requires register_open_relay_tool(mcp, 'better-telegram-mcp', "
        "PUBLIC_URL) to be called at module load in server.py."
    )


def test_config_open_relay_tool_callable():
    """The registered tool exposes a callable handler."""
    tool = mcp._tool_manager._tools["config__open_relay"]
    assert tool is not None
    # FastMCP tool wrapper exposes the original function via .fn
    assert callable(getattr(tool, "fn", None)) or callable(tool)
