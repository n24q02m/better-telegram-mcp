from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.server import (
    get_backend,
    get_settings,
    main,
    mcp,
)


def test_mcp_has_6_tools():
    tools = mcp._tool_manager._tools
    assert len(tools) == 6
    expected = {"messages", "chats", "media", "contacts", "config", "help"}
    assert set(tools.keys()) == expected


def test_main_exists():
    assert callable(main)


def test_get_backend_not_initialized():
    import better_telegram_mcp.server as srv

    old = srv._backend
    try:
        srv._backend = None
        with pytest.raises(RuntimeError, match="Backend not initialized"):
            get_backend()
    finally:
        srv._backend = old


def test_get_settings_not_initialized():
    import better_telegram_mcp.server as srv

    old = srv._settings
    try:
        srv._settings = None
        with pytest.raises(RuntimeError, match="Settings not initialized"):
            get_settings()
    finally:
        srv._settings = old


@pytest.mark.asyncio
async def test_messages_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import messages

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = await messages(srv.MessagesArgs(action="send", chat_id=123, text="hi"))
        assert "message_id" in result
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_chats_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import chats

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = await chats(action="list")
        assert "chats" in result
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_media_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import media

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = await media(
            action="send_photo",
            chat_id=123,
            file_path_or_url="https://example.com/photo.jpg",
        )
        assert "message_id" in result
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_contacts_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import contacts

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = await contacts(action="list")
        assert "contacts" in result
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_config_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

    old = srv._backend
    try:
        srv._backend = mock_backend
        result = await config(action="status")
        assert "mode" in result

        # Test set action through tool
        result = await config(action="set", message_limit=42)
        assert "updated" in result
    finally:
        srv._backend = old


@pytest.mark.asyncio
async def test_help_tool():
    from better_telegram_mcp.server import help

    result = await help(topic="messages")
    assert "Telegram Messages" in result


@pytest.mark.asyncio
async def test_lifespan_bot_mode(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan

    with patch.object(srv, "Settings") as mock_settings_cls:
        mock_settings = mock_settings_cls.return_value
        mock_settings.is_configured = True
        mock_settings.mode = "bot"
        mock_settings.bot_token = "fake:token"

        with patch(
            "better_telegram_mcp.server.BotBackend",
            create=True,
        ) as MockBot:
            mock_bot = AsyncMock()
            mock_bot.is_authorized = AsyncMock(return_value=True)
            MockBot.return_value = mock_bot

            with patch(
                "better_telegram_mcp.backends.bot_backend.BotBackend",
                MockBot,
            ):
                # Patch the import inside lifespan
                with patch.dict(
                    "sys.modules",
                    {
                        "better_telegram_mcp.backends.bot_backend": type(
                            "module", (), {"BotBackend": MockBot}
                        )()
                    },
                ):
                    async with _lifespan(mcp):
                        assert srv._backend is mock_bot
                        mock_bot.connect.assert_awaited_once()

                    mock_bot.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_user_mode():
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan

    mock_settings = MagicMock()
    mock_settings.is_configured = True
    mock_settings.mode = "user"
    mock_settings.api_id = 12345
    mock_settings.api_hash = "testhash"
    mock_settings.phone = "+84912345678"

    mock_user_backend = AsyncMock()
    mock_user_backend.is_authorized = AsyncMock(return_value=True)

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
        async with _lifespan(mcp):
            assert srv._backend is mock_user_backend
            mock_user_backend.connect.assert_awaited_once()

        mock_user_backend.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_user_mode_unauthorized_sets_pending():
    """When user mode session is unauthorized, set _pending_auth."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan

    mock_settings = MagicMock()
    mock_settings.is_configured = True
    mock_settings.mode = "user"
    mock_settings.api_id = 12345
    mock_settings.api_hash = "testhash"
    mock_settings.phone = "+84912345678"
    mock_settings.auth_url = "local"

    mock_user_backend = AsyncMock()
    mock_user_backend.is_authorized = AsyncMock(return_value=False)

    mock_handler = AsyncMock()

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
            patch(
                "better_telegram_mcp.server._start_auth",
                new_callable=AsyncMock,
                return_value=(mock_handler, "http://127.0.0.1:9999"),
            ),
            patch(
                "better_telegram_mcp.server._run_auth_background",
                new_callable=AsyncMock,
            ),
        ):
            async with _lifespan(mcp):
                assert srv._pending_auth is True
                mock_user_backend.send_code.assert_not_awaited()

            mock_user_backend.disconnect.assert_awaited_once()
    finally:
        srv._pending_auth = old_pending


# --- pending_auth behavior tests ---


@pytest.mark.asyncio
async def test_messages_blocked_during_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import messages

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(
            await messages(srv.MessagesArgs(action="send", chat_id=123, text="hi"))
        )
        assert "error" in result
        assert "not authenticated" in result["error"].lower()
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_chats_blocked_during_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import chats

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await chats(action="list"))
        assert "error" in result
        assert "not authenticated" in result["error"].lower()
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_media_blocked_during_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import media

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(
            await media(
                action="send_photo",
                chat_id=123,
                file_path_or_url="https://example.com/photo.jpg",
            )
        )
        assert "error" in result
        assert "not authenticated" in result["error"].lower()
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_contacts_blocked_during_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import contacts

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await contacts(action="list"))
        assert "error" in result
        assert "not authenticated" in result["error"].lower()
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_config_works_during_pending_auth(mock_backend):
    """Config tool should always work even during pending auth."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await config(action="status"))
        assert "mode" in result
        assert result["pending_auth"] is True
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_help_works_during_pending_auth():
    """Help tool should always work even during pending auth."""
    from better_telegram_mcp.server import help

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
    expected = {"messages", "chats", "media", "contacts", "config", "help"}
    assert set(tools.keys()) == expected


@pytest.mark.asyncio
async def test_help_works_without_credentials():
    """help tool works without any credentials."""
    from better_telegram_mcp.server import help

    result = await help(topic="messages")
    assert "Telegram Messages" in result

    result_all = await help(topic=None)
    assert "Telegram" in result_all


@pytest.mark.asyncio
async def test_messages_returns_setup_hint_when_unconfigured():
    """messages tool returns actionable setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import messages

    old_unconfigured = srv._unconfigured
    old_pending = srv._pending_auth
    try:
        srv._unconfigured = True
        srv._pending_auth = False
        result = json.loads(
            await messages(srv.MessagesArgs(action="send", chat_id=123, text="hi"))
        )
        assert "error" in result
        assert result["error"] == "Not configured"
        assert "setup" in result
        assert "bot_mode" in result["setup"]
        assert "TELEGRAM_BOT_TOKEN" in result["setup"]["bot_mode"]["env_var"]
        assert "user_mode" in result["setup"]
    finally:
        srv._unconfigured = old_unconfigured
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_chats_returns_setup_hint_when_unconfigured():
    """chats tool returns setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import chats

    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await chats(action="list"))
        assert result["error"] == "Not configured"
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_not_ready_response_unconfigured():
    import json

    import better_telegram_mcp.server as server

    server._unconfigured = True
    server._auth_url = None

    try:
        response = server._not_ready_response()
        data = json.loads(response)
        assert data["error"] == "Not configured"
        assert "bot_mode" in data["setup"]
        assert "user_mode" in data["setup"]
    finally:
        server._unconfigured = False


@pytest.mark.asyncio
async def test_not_ready_response_auth_url():
    import json

    import better_telegram_mcp.server as server

    server._unconfigured = False
    server._auth_url = "http://test.com/auth"

    try:
        response = server._not_ready_response()
        data = json.loads(response)
        assert "error" in data
        assert "http://test.com/auth" in data["error"]
    finally:
        server._auth_url = None


@pytest.mark.asyncio
async def test_not_ready_response_no_phone():
    import json

    import better_telegram_mcp.server as server

    server._unconfigured = False
    server._auth_url = None

    try:
        response = server._not_ready_response()
        data = json.loads(response)
        assert "error" in data
        assert "TELEGRAM_PHONE" in data["error"]
    finally:
        pass


@pytest.mark.asyncio
async def test_media_returns_setup_hint_when_unconfigured():
    """media tool returns setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import media

    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(
            await media(
                action="send_photo",
                chat_id=123,
                file_path_or_url="https://example.com/photo.jpg",
            )
        )
        assert result["error"] == "Not configured"
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_contacts_returns_setup_hint_when_unconfigured():
    """contacts tool returns setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import contacts

    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await contacts(action="list"))
        assert result["error"] == "Not configured"
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_config_status_works_when_unconfigured():
    """config status shows setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

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
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

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
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan

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

        async with _lifespan(mcp):
            assert srv._unconfigured is True

        assert srv._unconfigured is False
