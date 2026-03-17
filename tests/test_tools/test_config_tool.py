from __future__ import annotations

import json
from unittest.mock import MagicMock

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


# --- Auth action tests ---


@pytest.mark.asyncio
async def test_auth_success(mock_user_backend):
    import better_telegram_mcp.server as srv

    old_pending = srv._pending_auth
    old_settings = srv._settings
    try:
        srv._pending_auth = True
        mock_settings = MagicMock()
        mock_settings.phone = "+84912345678"
        srv._settings = mock_settings

        result = json.loads(
            await handle_config(mock_user_backend, "auth", code="12345")
        )

        assert "message" in result
        assert "Authentication successful" in result["message"]
        assert result["authenticated_as"] == "Test"
        assert srv._pending_auth is False
        mock_user_backend.sign_in.assert_awaited_once_with(
            "+84912345678", "12345", password=None
        )
    finally:
        srv._pending_auth = old_pending
        srv._settings = old_settings


@pytest.mark.asyncio
async def test_auth_with_2fa_password(mock_user_backend):
    import better_telegram_mcp.server as srv

    old_pending = srv._pending_auth
    old_settings = srv._settings
    try:
        srv._pending_auth = True
        mock_settings = MagicMock()
        mock_settings.phone = "+84912345678"
        srv._settings = mock_settings

        result = json.loads(
            await handle_config(
                mock_user_backend, "auth", code="12345", password="my2fapass"
            )
        )

        assert "Authentication successful" in result["message"]
        mock_user_backend.sign_in.assert_awaited_once_with(
            "+84912345678", "12345", password="my2fapass"
        )
    finally:
        srv._pending_auth = old_pending
        srv._settings = old_settings


@pytest.mark.asyncio
async def test_auth_no_code(mock_user_backend):
    import better_telegram_mcp.server as srv

    old = srv._pending_auth
    try:
        srv._pending_auth = True
        result = json.loads(await handle_config(mock_user_backend, "auth"))
        assert "error" in result
        assert "code" in result["error"]
    finally:
        srv._pending_auth = old


@pytest.mark.asyncio
async def test_auth_no_phone(mock_user_backend):
    import better_telegram_mcp.server as srv

    old_pending = srv._pending_auth
    old_settings = srv._settings
    try:
        srv._pending_auth = True
        mock_settings = MagicMock()
        mock_settings.phone = None
        srv._settings = mock_settings

        result = json.loads(
            await handle_config(mock_user_backend, "auth", code="12345")
        )
        assert "error" in result
        assert "TELEGRAM_PHONE" in result["error"]
    finally:
        srv._pending_auth = old_pending
        srv._settings = old_settings


@pytest.mark.asyncio
async def test_auth_already_authenticated(mock_user_backend):
    import better_telegram_mcp.server as srv

    old = srv._pending_auth
    try:
        srv._pending_auth = False
        result = json.loads(
            await handle_config(mock_user_backend, "auth", code="12345")
        )
        assert "Already authenticated" in result["message"]
    finally:
        srv._pending_auth = old


@pytest.mark.asyncio
async def test_auth_sign_in_error(mock_user_backend):
    import better_telegram_mcp.server as srv

    old_pending = srv._pending_auth
    old_settings = srv._settings
    try:
        srv._pending_auth = True
        mock_settings = MagicMock()
        mock_settings.phone = "+84912345678"
        srv._settings = mock_settings

        mock_user_backend.sign_in.side_effect = Exception("PhoneCodeInvalid")
        result = json.loads(
            await handle_config(mock_user_backend, "auth", code="wrong")
        )
        assert "error" in result
        assert (
            "Operation failed" in result["error"]
            or "PhoneCodeInvalid" in result["error"]
        )
    finally:
        srv._pending_auth = old_pending
        srv._settings = old_settings


# --- send_code action tests ---


@pytest.mark.asyncio
async def test_send_code_success(mock_user_backend):
    import better_telegram_mcp.server as srv

    old_pending = srv._pending_auth
    old_settings = srv._settings
    try:
        srv._pending_auth = False
        mock_settings = MagicMock()
        mock_settings.phone = "+84912345678"
        srv._settings = mock_settings

        result = json.loads(await handle_config(mock_user_backend, "send_code"))
        assert "OTP code sent" in result["message"]
        assert srv._pending_auth is True
        mock_user_backend.send_code.assert_awaited_once_with("+84912345678")
    finally:
        srv._pending_auth = old_pending
        srv._settings = old_settings


@pytest.mark.asyncio
async def test_send_code_no_phone(mock_user_backend):
    import better_telegram_mcp.server as srv

    old_settings = srv._settings
    try:
        mock_settings = MagicMock()
        mock_settings.phone = None
        srv._settings = mock_settings

        result = json.loads(await handle_config(mock_user_backend, "send_code"))
        assert "error" in result
        assert "TELEGRAM_PHONE" in result["error"]
    finally:
        srv._settings = old_settings
