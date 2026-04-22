from __future__ import annotations

import json
import os
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
    expected = {"message", "chat", "media", "contact", "config", "help"}
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
async def test_message_send(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import message

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = await message(action="send", chat_id=123, text="hi")
        assert "message_id" in result
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_chat_list(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import chat

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = await chat(action="list")
        assert "chats" in result
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_media_send_photo(mock_backend):
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
async def test_contact_list(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import contact

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = await contact(action="list")
        assert "contacts" in result
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_message_unknown_action(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import message

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = False
        result = json.loads(await message(action="nonexistent"))
        assert "error" in result
        assert "Unknown action" in result["error"]
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


# --- pending_auth behavior tests ---


@pytest.mark.asyncio
async def test_message_blocked_during_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import message

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await message(action="send", chat_id=123, text="hi"))
        assert "error" in result
        assert "not authenticated" in result["error"].lower()
    finally:
        srv._backend = old_backend
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_chat_blocked_during_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import chat

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await chat(action="list"))
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
async def test_contact_blocked_during_pending_auth(mock_backend):
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import contact

    old_backend = srv._backend
    old_pending = srv._pending_auth
    try:
        srv._backend = mock_backend
        srv._pending_auth = True
        result = json.loads(await contact(action="list"))
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
    with (
        patch("better_telegram_mcp.server.mcp.run") as mock_run,
        patch.dict(os.environ, {"MCP_TRANSPORT": "stdio"}),
        pytest.raises(SystemExit, match="0"),
    ):
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
    from better_telegram_mcp.server import help

    result = await help(topic="messages")
    assert "Telegram Messages" in result

    result_all = await help(topic=None)
    assert "Telegram" in result_all


@pytest.mark.asyncio
async def test_message_returns_setup_hint_when_unconfigured():
    """message tool returns actionable setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import message

    old_unconfigured = srv._unconfigured
    old_pending = srv._pending_auth
    try:
        srv._unconfigured = True
        srv._pending_auth = False
        result = json.loads(await message(action="send", chat_id=123, text="hi"))
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
async def test_chat_returns_setup_hint_when_unconfigured():
    """chat tool returns setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import chat

    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await chat(action="list"))
        assert result["error"] == "Not configured"
        assert "setup" in result
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_not_ready_response_unconfigured():
    import better_telegram_mcp.server as server

    old = server._unconfigured
    try:
        server._unconfigured = True
        response = server._not_ready_response()
        data = json.loads(response)
        assert data["error"] == "Not configured"
        assert "bot_mode" in data["setup"]
        assert "user_mode" in data["setup"]
    finally:
        server._unconfigured = old


@pytest.mark.asyncio
async def test_not_ready_response_pending_auth():
    import better_telegram_mcp.server as server

    old_unconfigured = server._unconfigured
    old_pending = server._pending_auth
    try:
        server._unconfigured = False
        server._pending_auth = True
        response = server._not_ready_response()
        data = json.loads(response)
        assert "error" in data
        assert "not authenticated" in data["error"].lower()
    finally:
        server._unconfigured = old_unconfigured
        server._pending_auth = old_pending


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
async def test_contact_returns_setup_hint_when_unconfigured():
    """contact tool returns setup instructions when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import contact

    old = srv._unconfigured
    try:
        srv._unconfigured = True
        result = json.loads(await contact(action="list"))
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
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import _lifespan

    with (
        patch.object(srv, "Settings") as mock_settings_cls,
        patch(
            "better_telegram_mcp.credential_state.resolve_credential_state",
            return_value=CredentialState.AWAITING_SETUP,
        ),
    ):
        mock_settings = mock_settings_cls.return_value
        mock_settings.is_configured = False

        async with _lifespan(mcp):
            assert srv._unconfigured is True

        assert srv._unconfigured is False


# --- setup_* config actions (credential state integration) ---


@pytest.mark.asyncio
async def test_config_setup_status():
    """setup_status returns credential state info."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

    old_unconfigured = srv._unconfigured
    old_pending = srv._pending_auth
    try:
        srv._unconfigured = False
        srv._pending_auth = False

        with (
            patch(
                "better_telegram_mcp.credential_state.get_state",
                return_value=MagicMock(value="configured"),
            ),
            patch(
                "better_telegram_mcp.credential_state.get_setup_url",
                return_value=None,
            ),
        ):
            result = json.loads(await config(action="setup_status"))
            assert result["state"] == "configured"
            assert "setup_url" in result
            assert "configured" in result
            assert "pending_auth" in result
    finally:
        srv._unconfigured = old_unconfigured
        srv._pending_auth = old_pending


@pytest.mark.asyncio
async def test_config_setup_start_already_configured():
    """setup_start returns already_configured if state is CONFIGURED without force."""
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import config

    with patch(
        "better_telegram_mcp.credential_state.get_state",
        return_value=CredentialState.CONFIGURED,
    ):
        result = json.loads(await config(action="setup_start"))
        assert result["status"] == "already_configured"
        assert "force" in result["message"].lower()


@pytest.mark.asyncio
async def test_config_setup_start_force():
    """setup_start with key='force' triggers relay even when configured."""
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import config

    with (
        patch(
            "better_telegram_mcp.credential_state.get_state",
            return_value=CredentialState.CONFIGURED,
        ),
        patch(
            "better_telegram_mcp.credential_state.trigger_relay_setup",
            new_callable=AsyncMock,
            return_value="https://relay.example.com/setup",
        ),
    ):
        result = json.loads(await config(action="setup_start", key="force"))
        assert result["status"] == "setup_started"
        assert result["setup_url"] == "https://relay.example.com/setup"


@pytest.mark.asyncio
async def test_config_setup_start_awaiting():
    """setup_start when awaiting -> triggers relay."""
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import config

    with (
        patch(
            "better_telegram_mcp.credential_state.get_state",
            return_value=CredentialState.AWAITING_SETUP,
        ),
        patch(
            "better_telegram_mcp.credential_state.trigger_relay_setup",
            new_callable=AsyncMock,
            return_value="https://relay.example.com/new-setup",
        ),
    ):
        result = json.loads(await config(action="setup_start"))
        assert result["status"] == "setup_started"
        assert "new-setup" in result["setup_url"]


@pytest.mark.asyncio
async def test_config_setup_start_relay_fails():
    """setup_start when relay fails -> returns error."""
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import config

    with (
        patch(
            "better_telegram_mcp.credential_state.get_state",
            return_value=CredentialState.AWAITING_SETUP,
        ),
        patch(
            "better_telegram_mcp.credential_state.trigger_relay_setup",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        result = json.loads(await config(action="setup_start"))
        assert "error" in result
        assert "Failed" in result["error"]


@pytest.mark.asyncio
async def test_config_setup_reset():
    """setup_reset clears credentials."""
    from better_telegram_mcp.server import config

    with patch("better_telegram_mcp.credential_state.reset_state") as mock_reset:
        result = json.loads(await config(action="setup_reset"))
        assert result["status"] == "ok"
        assert "cleared" in result["message"].lower()
        mock_reset.assert_called_once()


@pytest.mark.asyncio
async def test_config_setup_complete():
    """setup_complete re-resolves credential state."""
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import config

    with (
        patch(
            "better_telegram_mcp.credential_state.resolve_credential_state",
            return_value=CredentialState.CONFIGURED,
        ),
        patch(
            "better_telegram_mcp.credential_state.get_state",
            return_value=CredentialState.CONFIGURED,
        ),
    ):
        result = json.loads(await config(action="setup_complete"))
        assert result["status"] == "ok"
        assert result["state"] == "configured"


@pytest.mark.asyncio
async def test_config_setup_status_works_when_unconfigured():
    """setup_status works even when server is unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

    old = srv._unconfigured
    try:
        srv._unconfigured = True
        with (
            patch(
                "better_telegram_mcp.credential_state.get_state",
                return_value=MagicMock(value="awaiting_setup"),
            ),
            patch(
                "better_telegram_mcp.credential_state.get_setup_url",
                return_value=None,
            ),
        ):
            result = json.loads(await config(action="setup_status"))
            assert result["state"] == "awaiting_setup"
    finally:
        srv._unconfigured = old


@pytest.mark.asyncio
async def test_config_setup_reset_works_when_unconfigured():
    """setup_reset works even when server is unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import config

    old = srv._unconfigured
    try:
        srv._unconfigured = True
        with patch("better_telegram_mcp.credential_state.reset_state"):
            result = json.loads(await config(action="setup_reset"))
            assert result["status"] == "ok"
    finally:
        srv._unconfigured = old


# --- lifespan: resolve_credential_state integration ---


@pytest.mark.asyncio
async def test_lifespan_resolves_credentials_when_unconfigured():
    """Lifespan calls resolve_credential_state and re-creates Settings if configured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan

    mock_settings_initial = MagicMock()
    mock_settings_initial.is_configured = False

    mock_settings_reconfigured = MagicMock()
    mock_settings_reconfigured.is_configured = True
    mock_settings_reconfigured.mode = "bot"
    mock_settings_reconfigured.bot_token = "resolved:token"

    mock_bot = AsyncMock()
    mock_bot.is_authorized = AsyncMock(return_value=True)

    settings_call_count = 0

    def settings_factory(*args, **kwargs):
        nonlocal settings_call_count
        settings_call_count += 1
        if settings_call_count == 1:
            return mock_settings_initial
        return mock_settings_reconfigured

    from better_telegram_mcp.credential_state import CredentialState

    with (
        patch.object(srv, "Settings", side_effect=settings_factory),
        patch(
            "better_telegram_mcp.credential_state.resolve_credential_state",
            return_value=CredentialState.CONFIGURED,
        ),
        patch.dict(
            "sys.modules",
            {
                "better_telegram_mcp.backends.bot_backend": type(
                    "module",
                    (),
                    {"BotBackend": MagicMock(return_value=mock_bot)},
                )()
            },
        ),
    ):
        async with _lifespan(mcp):
            assert srv._settings is mock_settings_reconfigured
            mock_bot.connect.assert_awaited_once()

        mock_bot.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_multi_user_mode_unconfigured():
    """Multi-user mode starts without global backend when unconfigured."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan

    old_multi = srv._multi_user_mode
    try:
        srv._multi_user_mode = True

        mock_settings = MagicMock()
        mock_settings.is_configured = False

        with (
            patch.object(srv, "Settings", return_value=mock_settings),
            patch(
                "better_telegram_mcp.credential_state.resolve_credential_state",
                return_value=MagicMock(value="awaiting_setup"),
            ),
        ):
            async with _lifespan(mcp):
                # In multi-user mode, unconfigured is OK
                assert srv._unconfigured is not True
    finally:
        srv._multi_user_mode = old_multi


# --- get_backend multi-user mode ---


def test_get_backend_multi_user_mode():
    """get_backend returns per-user backend in multi-user mode."""
    import better_telegram_mcp.server as srv

    old_multi = srv._multi_user_mode
    old_backend = srv._backend
    try:
        srv._multi_user_mode = True
        mock_per_user = MagicMock()

        with patch(
            "better_telegram_mcp.transports.http.get_current_backend",
            return_value=mock_per_user,
        ):
            result = get_backend()
            assert result is mock_per_user
    finally:
        srv._multi_user_mode = old_multi
        srv._backend = old_backend


def test_get_backend_multi_user_mode_fallback():
    """get_backend falls back to global backend when ContextVar is None."""
    import better_telegram_mcp.server as srv

    old_multi = srv._multi_user_mode
    old_backend = srv._backend
    try:
        srv._multi_user_mode = True
        srv._backend = MagicMock()

        with patch(
            "better_telegram_mcp.transports.http.get_current_backend",
            return_value=None,
        ):
            result = get_backend()
            assert result is srv._backend
    finally:
        srv._multi_user_mode = old_multi
        srv._backend = old_backend


# --- main() HTTP transport ---


def test_main_http_transport():
    """main() dispatches HTTP through transports.http.start_http so the
    multi-user OAuth branch + refuse-guard + local-relay fallback all live
    behind one entry point."""
    with (
        patch("better_telegram_mcp.transports.http.start_http") as mock_start_http,
        patch.dict(os.environ, {}, clear=True),
    ):
        main()
        mock_start_http.assert_called_once()


# --- lifespan: user mode unauthorized, no phone, no relay ---


@pytest.mark.asyncio
async def test_lifespan_user_mode_unauthorized_no_phone():
    """Lifespan sets pending_auth when session unauthorized and phone is not set."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan

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
            async with _lifespan(mcp):
                assert srv._pending_auth is True
                # pending_auth set without auth flow

            mock_user_backend.disconnect.assert_awaited_once()
    finally:
        srv._pending_auth = old_pending
