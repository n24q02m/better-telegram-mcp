from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import better_telegram_mcp.server as srv
from better_telegram_mcp.server import (
    chat,
    config,
    contact,
    get_backend,
    help,
    main,
    mcp,
    media,
    message,
)
from better_telegram_mcp.tools.chats import ChatOptions
from better_telegram_mcp.tools.contacts import ContactsOptions
from better_telegram_mcp.tools.media import MediaOptions
from better_telegram_mcp.tools.messages import MessagesArgs


@pytest.fixture
def mock_backend():
    backend = AsyncMock()
    backend.send_message.return_value = {"message_id": 1, "text": "hello"}
    backend.list_chats.return_value = []
    backend.send_media.return_value = {"message_id": 3}
    backend.list_contacts.return_value = []
    backend.is_authorized.return_value = True
    return backend


@pytest.mark.asyncio
async def test_get_backend_not_initialized():
    old_backend = srv._backend
    srv._backend = None
    try:
        with pytest.raises(RuntimeError, match="Backend not initialized"):
            get_backend()
    finally:
        srv._backend = old_backend


@pytest.mark.asyncio
async def test_message_send(mock_backend):
    old_backend = srv._backend
    try:
        srv._backend = mock_backend
        result = await message(MessagesArgs(action="send", chat_id=123, text="hello"))
        assert "message_id" in result
        mock_backend.send_message.assert_awaited_once()
    finally:
        srv._backend = old_backend


@pytest.mark.asyncio
async def test_chat_list(mock_backend):
    old_backend = srv._backend
    try:
        srv._backend = mock_backend
        result = await chat(ChatOptions(action="list"))
        assert "chats" in result
        mock_backend.list_chats.assert_awaited_once()
    finally:
        srv._backend = old_backend


@pytest.mark.asyncio
async def test_media_send(mock_backend):
    old_backend = srv._backend
    try:
        srv._backend = mock_backend
        result = await media(
            MediaOptions(
                action="send_photo",
                chat_id=123,
                file_path_or_url="https://example.com/photo.jpg",
            )
        )
        assert "message_id" in result
        mock_backend.send_media.assert_awaited_once()
    finally:
        srv._backend = old_backend


@pytest.mark.asyncio
async def test_contact_list(mock_backend):
    old_backend = srv._backend
    try:
        srv._backend = mock_backend
        result = await contact(ContactsOptions(action="list"))
        assert "contacts" in result
        mock_backend.list_contacts.assert_awaited_once()
    finally:
        srv._backend = old_backend


@pytest.mark.asyncio
async def test_media_blocked_during_pending_auth(mock_backend):
    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(
            await media(
                MediaOptions(
                    action="send_photo",
                    chat_id=123,
                    file_path_or_url="https://example.com/photo.jpg",
                )
            )
        )
        assert "error" in result
        assert "not authenticated" in result["error"].lower()
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_contact_blocked_during_pending_auth(mock_backend):
    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await contact(ContactsOptions(action="list")))
        assert "error" in result
        assert "not authenticated" in result["error"].lower()
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_config_works_during_pending_auth(mock_backend):
    """Config tool should always work even during pending auth."""
    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await config(action="status"))
        assert "mode" in result
        # The key is "pending_auth" in the response of _not_ready_response or status?
        # Actually in server.py action="status" it's:
        # return await handle_config(get_backend(), action, ...)
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_help_works_during_pending_auth():
    """Help tool should always work even during pending auth."""
    result = await help(topic="messages")
    assert "Telegram Messages" in result


def test_main_calls_run():
    with patch.object(mcp, "run") as mock_run:
        main()
        mock_run.assert_called_once_with(transport="stdio")


# --- unconfigured state tests (no credentials) ---


@pytest.mark.asyncio
async def test_tools_list_works_without_credentials():
    """tools/list should work even with no Telegram credentials."""
    tools = mcp._tool_manager._tools
    assert len(tools) == 6
    expected = {"message", "chat", "media", "contact", "config", "help"}
    assert set(tools.keys()) == expected


@pytest.mark.asyncio
async def test_help_works_without_credentials():
    """help tool works without any credentials."""
    result = await help(topic="messages")
    assert "Telegram Messages" in result

    result_all = await help(topic=None)
    assert "Telegram" in result_all


@pytest.mark.asyncio
async def test_message_returns_setup_hint_when_unconfigured():
    """message tool returns actionable setup instructions when unconfigured."""
    old_unconfigured = srv._unconfigured
    old_pending = srv._pending_auth
    try:
        srv._unconfigured = True
        srv._pending_auth = False
        result = json.loads(
            await message(MessagesArgs(action="send", chat_id=123, text="hi"))
        )
        assert "error" in result
        assert result["error"] == "Not configured"
        assert "setup" in result
        assert "bot_mode" in result["setup"]
    finally:
        srv._unconfigured = old_unconfigured
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_chat_returns_setup_hint_when_unconfigured():
    """chat tool returns setup instructions when unconfigured."""
    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await chat(ChatOptions(action="list")))
        assert result["error"] == "Not configured"
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_not_ready_response_unconfigured():
    old = srv._unconfigured
    try:
        srv._unconfigured = True
        response = srv._not_ready_response()
        data = json.loads(response)
        assert data["error"] == "Not configured"
        assert "bot_mode" in data["setup"]
        assert "user_mode" in data["setup"]
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_not_ready_response_pending_auth():
    old_unconfigured = srv._unconfigured
    old_pending = srv._pending_auth
    try:
        srv._unconfigured = False
        srv._pending_auth = True
        response = srv._not_ready_response()
        data = json.loads(response)
        assert "error" in data
        assert "not authenticated" in data["error"].lower()
    finally:
        srv._unconfigured = old_unconfigured
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_media_returns_setup_hint_when_unconfigured():
    """media tool returns setup instructions when unconfigured."""
    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(
            await media(
                MediaOptions(
                    action="send_photo",
                    chat_id=123,
                    file_path_or_url="https://example.com/photo.jpg",
                )
            )
        )
        assert result["error"] == "Not configured"
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_contact_returns_setup_hint_when_unconfigured():
    """contact tool returns setup instructions when unconfigured."""
    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await contact(ContactsOptions(action="list")))
        assert result["error"] == "Not configured"
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_config_status_works_when_unconfigured():
    """config status shows setup instructions when unconfigured."""
    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await config(action="status"))
        assert result["configured"] is False
        assert result["connected"] is False
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_config_set_blocked_when_unconfigured():
    """config set returns setup instructions when unconfigured."""
    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await config(action="set", message_limit=42))
        assert result["error"] == "Not configured"
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_lifespan_unconfigured_mode():
    """Lifespan should start successfully without credentials."""
    with (
        patch.object(srv, "Settings") as mock_settings_cls,
        patch(
            "better_telegram_mcp.relay_setup.ensure_config",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        mock_settings = mock_settings_cls.return_value
        mock_settings.is_configured = False

        async with srv._lifespan(mcp):
            assert srv._unconfigured is True

        assert srv._unconfigured is False


# --- main() HTTP transport ---


def test_main_http_transport():
    """main() starts HTTP transport when TRANSPORT_MODE=http."""
    import os

    with (
        patch.dict(os.environ, {"TRANSPORT_MODE": "http"}),
        patch("better_telegram_mcp.transports.http.start_http") as mock_start_http,
    ):
        main()
        mock_start_http.assert_called_once()


# --- lifespan: user mode unauthorized, no phone, no relay ---


@pytest.mark.asyncio
async def test_lifespan_user_mode_unauthorized_no_phone():
    """Lifespan sets pending_auth when session unauthorized and phone is not set."""
    mock_settings = MagicMock()
    mock_settings.is_configured = True
    mock_settings.mode = "user"
    mock_settings.api_id = 12345
    mock_settings.api_hash = "testhash"
    mock_settings.phone = None  # No phone set

    mock_user_backend = AsyncMock()
    mock_user_backend.is_authorized = AsyncMock(return_value=False)

    old_pending = srv._pending_auth
    try:
        with (
            patch.object(srv, "Settings", return_value=mock_settings),
            patch.dict(
                "sys.modules",
                {
                    "better_telegram_mcp.backends.user_backend": type(
                        "module",
                        (),
                        {"UserBackend": MagicMock(return_value=mock_user_backend)},
                    )()
                },
            ),
        ):
            async with srv._lifespan(mcp):
                assert srv._pending_auth is True
                # pending_auth set without auth flow

            mock_user_backend.disconnect.assert_awaited_once()
    finally:
        srv._pending_auth = old_pending
