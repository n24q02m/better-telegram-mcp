from __future__ import annotations

import json

import pytest

from better_telegram_mcp.tools.config_tool import handle_config


@pytest.mark.asyncio
async def test_status(mock_backend):
    result = json.loads(await handle_config(mock_backend, "status"))
    assert result["mode"] == "bot"
    assert result["connected"] is True
    assert result["authorized"] is True
    assert "config" in result
    assert "message_limit" in result["config"]
    assert "timeout" in result["config"]


@pytest.mark.asyncio
async def test_status_user_mode(mock_user_backend):
    result = json.loads(await handle_config(mock_user_backend, "status"))
    assert result["mode"] == "user"
    assert result["connected"] is True
    assert result["authorized"] is True


@pytest.mark.asyncio
async def test_status_shows_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv

    old = srv._pending_auth
    try:
        srv._pending_auth = True
        result = json.loads(await handle_config(mock_backend, "status"))
        assert result["pending_auth"] is True
    finally:
        srv._pending_auth = old


@pytest.mark.asyncio
async def test_set_message_limit(mock_backend):
    result = json.loads(await handle_config(mock_backend, "set", message_limit=50))
    assert result["updated"]["message_limit"] == 50
    assert result["current"]["message_limit"] == 50


@pytest.mark.asyncio
async def test_set_timeout(mock_backend):
    result = json.loads(await handle_config(mock_backend, "set", timeout=60))
    assert result["updated"]["timeout"] == 60
    assert result["current"]["timeout"] == 60


@pytest.mark.asyncio
async def test_set_both(mock_backend):
    result = json.loads(
        await handle_config(mock_backend, "set", message_limit=100, timeout=90)
    )
    assert result["updated"]["message_limit"] == 100
    assert result["updated"]["timeout"] == 90


@pytest.mark.asyncio
async def test_set_no_params(mock_backend):
    result = json.loads(await handle_config(mock_backend, "set"))
    assert "error" in result
    assert "set requires" in result["error"]


@pytest.mark.asyncio
async def test_set_none_params(mock_backend):
    result = json.loads(
        await handle_config(mock_backend, "set", message_limit=None, timeout=None)
    )
    assert "error" in result
    assert "set requires" in result["error"]


@pytest.mark.asyncio
async def test_set_persists_across_calls(mock_backend):
    await handle_config(mock_backend, "set", message_limit=42)
    result = json.loads(await handle_config(mock_backend, "status"))
    assert result["config"]["message_limit"] == 42


@pytest.mark.asyncio
async def test_cache_clear(mock_backend):
    result = json.loads(await handle_config(mock_backend, "cache_clear"))
    assert "message" in result
    assert "Cache cleared" in result["message"]
    mock_backend.clear_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_clear_user_mode(mock_user_backend):
    result = json.loads(await handle_config(mock_user_backend, "cache_clear"))
    assert "Cache cleared" in result["message"]
    mock_user_backend.clear_cache.assert_awaited_once()


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


# Auth/send_code actions removed — auth handled by mcp-core's local OAuth
# AS in HTTP mode (browser paste form + OTP /otp endpoint), not by the
# config tool.


@pytest.mark.asyncio
async def test_unknown_action_suggestion(mock_backend):
    result = json.loads(await handle_config(mock_backend, "statu"))
    assert "error" in result
    assert "Did you mean 'status'?" in result["error"]


@pytest.mark.asyncio
async def test_set_invalid_int(mock_backend):
    result = json.loads(
        await handle_config(mock_backend, "set", message_limit="invalid")
    )
    assert "error" in result
    assert "ValueError" in result["error"]
