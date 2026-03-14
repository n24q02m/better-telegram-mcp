from __future__ import annotations

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

    old = srv._backend
    try:
        srv._backend = mock_backend
        result = await messages(action="send", chat_id=123, text="hi")
        assert "message_id" in result
    finally:
        srv._backend = old


@pytest.mark.asyncio
async def test_chats_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import chats

    old = srv._backend
    try:
        srv._backend = mock_backend
        result = await chats(action="list")
        assert "chats" in result
    finally:
        srv._backend = old


@pytest.mark.asyncio
async def test_media_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import media

    old = srv._backend
    try:
        srv._backend = mock_backend
        result = await media(
            action="send_photo",
            chat_id=123,
            file_path_or_url="https://example.com/photo.jpg",
        )
        assert "message_id" in result
    finally:
        srv._backend = old


@pytest.mark.asyncio
async def test_contacts_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import contacts

    old = srv._backend
    try:
        srv._backend = mock_backend
        result = await contacts(action="list")
        assert "contacts" in result
    finally:
        srv._backend = old


@pytest.mark.asyncio
async def test_config_tool(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

    old = srv._backend
    try:
        srv._backend = mock_backend
        result = await config(action="status")
        assert "mode" in result
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
        mock_settings.mode = "bot"
        mock_settings.bot_token = "fake:token"

        with patch(
            "better_telegram_mcp.server.BotBackend",
            create=True,
        ) as MockBot:
            mock_bot = AsyncMock()
            MockBot.return_value = mock_bot

            with patch(
                "better_telegram_mcp.backends.bot_backend.BotBackend",
                MockBot,
            ):
                # Patch the import inside lifespan
                with patch.dict(
                    "sys.modules",
                    {"better_telegram_mcp.backends.bot_backend": type(
                        "module", (), {"BotBackend": MockBot}
                    )()},
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
    mock_settings.mode = "user"
    mock_settings.api_id = 12345
    mock_settings.api_hash = "testhash"

    mock_user_backend = AsyncMock()

    with (
        patch.object(srv, "Settings", return_value=mock_settings),
        patch.dict(
            "sys.modules",
            {"better_telegram_mcp.backends.user_backend": type(
                "module", (), {"UserBackend": MagicMock(return_value=mock_user_backend)}
            )()},
        ),
    ):
        async with _lifespan(mcp):
            assert srv._backend is mock_user_backend
            mock_user_backend.connect.assert_awaited_once()

        mock_user_backend.disconnect.assert_awaited_once()


def test_main_calls_run():
    with patch.object(mcp, "run") as mock_run:
        main()
        mock_run.assert_called_once_with(transport="stdio")
