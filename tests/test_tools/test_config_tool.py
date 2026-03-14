from __future__ import annotations

import json

import pytest

from better_telegram_mcp.tools.config_tool import handle_config


@pytest.mark.asyncio
async def test_status(mock_backend):
    result = json.loads(await handle_config(mock_backend, "status"))
    assert result["mode"] == "bot"
    assert result["connected"] is True


@pytest.mark.asyncio
async def test_status_user_mode(mock_user_backend):
    result = json.loads(await handle_config(mock_user_backend, "status"))
    assert result["mode"] == "user"
    assert result["connected"] is True


@pytest.mark.asyncio
async def test_set(mock_backend):
    result = json.loads(await handle_config(mock_backend, "set"))
    assert "message" in result
    assert "environment variables" in result["message"]


@pytest.mark.asyncio
async def test_cache_clear(mock_backend):
    result = json.loads(await handle_config(mock_backend, "cache_clear"))
    assert "message" in result
    assert "Cache cleared" in result["message"]


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(await handle_config(mock_backend, "unknown"))
    assert "error" in result
    assert "Unknown action" in result["error"]


@pytest.mark.asyncio
async def test_general_exception(mock_backend):
    mock_backend.is_connected.side_effect = RuntimeError("fail")
    result = json.loads(await handle_config(mock_backend, "status"))
    assert "error" in result
    assert "RuntimeError" in result["error"]
