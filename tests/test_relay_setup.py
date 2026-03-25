"""Tests for relay setup integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings

# --- Settings.from_relay_config ---


def test_from_relay_config_bot_mode():
    """Create Settings from relay config with bot token."""
    config = {"TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"}
    s = Settings.from_relay_config(config)
    assert s.bot_token == "123456:ABC-DEF"
    assert s.mode == "bot"
    assert s.is_configured is True


def test_from_relay_config_user_mode():
    """Create Settings from relay config with user credentials."""
    config = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdef123456",
        "TELEGRAM_PHONE": "+84912345678",
    }
    s = Settings.from_relay_config(config)
    assert s.api_id == 12345
    assert s.api_hash == "abcdef123456"
    assert s.phone == "+84912345678"
    assert s.mode == "user"
    assert s.is_configured is True


def test_from_relay_config_empty_values():
    """Empty values in relay config should result in unconfigured state."""
    config = {"TELEGRAM_BOT_TOKEN": ""}
    s = Settings.from_relay_config(config)
    assert s.bot_token is None  # _empty_to_none normalizes it
    assert s.is_configured is False


def test_from_relay_config_missing_keys():
    """Missing keys should result in None values."""
    config = {}
    s = Settings.from_relay_config(config)
    assert s.bot_token is None
    assert s.api_id is None
    assert s.is_configured is False


# --- ensure_config ---


@pytest.mark.asyncio
async def test_ensure_config_returns_config_file_data():
    """ensure_config returns data from config file when available."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result = MagicMock()
    mock_result.config = {"TELEGRAM_BOT_TOKEN": "from-file:TOKEN"}
    mock_result.source = "file"

    with patch(
        "better_telegram_mcp.relay_setup.resolve_config",
        return_value=mock_result,
    ):
        result = await ensure_config()

    assert result is not None
    assert result["TELEGRAM_BOT_TOKEN"] == "from-file:TOKEN"


@pytest.mark.asyncio
async def test_ensure_config_checks_user_mode_fields():
    """ensure_config checks user mode fields if bot mode fields not found."""
    from better_telegram_mcp.relay_setup import ensure_config

    # First call (bot fields) returns None, second call (user fields) returns config
    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_result_user = MagicMock()
    mock_result_user.config = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdef",
    }
    mock_result_user.source = "file"

    with patch(
        "better_telegram_mcp.relay_setup.resolve_config",
        side_effect=[mock_result_none, mock_result_user],
    ):
        result = await ensure_config()

    assert result is not None
    assert result["TELEGRAM_API_ID"] == "12345"


@pytest.mark.asyncio
async def test_ensure_config_triggers_relay_when_nothing_found():
    """ensure_config triggers relay setup when no config found anywhere."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"

    expected_config = {"TELEGRAM_BOT_TOKEN": "relay:TOKEN"}

    with (
        patch(
            "better_telegram_mcp.relay_setup.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "better_telegram_mcp.relay_setup.poll_for_result",
            new_callable=AsyncMock,
            return_value=expected_config,
        ),
        patch(
            "better_telegram_mcp.relay_setup.write_config",
        ) as mock_write,
    ):
        result = await ensure_config()

    assert result is not None
    assert result["TELEGRAM_BOT_TOKEN"] == "relay:TOKEN"
    mock_write.assert_called_once_with("better-telegram-mcp", expected_config)


@pytest.mark.asyncio
async def test_ensure_config_returns_none_when_relay_unreachable():
    """ensure_config returns None when relay server is unreachable."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    with (
        patch(
            "better_telegram_mcp.relay_setup.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.create_session",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Cannot connect"),
        ),
    ):
        result = await ensure_config()

    assert result is None


@pytest.mark.asyncio
async def test_ensure_config_returns_none_on_poll_timeout():
    """ensure_config returns None when relay polling times out."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"

    with (
        patch(
            "better_telegram_mcp.relay_setup.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "better_telegram_mcp.relay_setup.poll_for_result",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Relay setup timed out"),
        ),
    ):
        result = await ensure_config()

    assert result is None


# --- Lifespan integration ---


@pytest.mark.asyncio
async def test_lifespan_tries_relay_when_unconfigured():
    """Lifespan should attempt relay setup when no env vars are set."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan, mcp

    relay_config = {"TELEGRAM_BOT_TOKEN": "relay:TOKEN"}

    mock_bot = AsyncMock()
    mock_bot.is_authorized = AsyncMock(return_value=True)

    # Create a mock Settings class that returns unconfigured first,
    # then configured when from_relay_config is called
    unconfigured_settings = MagicMock(is_configured=False)
    configured_settings = MagicMock(
        is_configured=True,
        mode="bot",
        bot_token="relay:TOKEN",
    )

    mock_settings_cls = MagicMock(return_value=unconfigured_settings)
    mock_settings_cls.from_relay_config = MagicMock(return_value=configured_settings)

    with (
        patch.object(srv, "Settings", mock_settings_cls),
        patch(
            "better_telegram_mcp.relay_setup.ensure_config",
            new_callable=AsyncMock,
            return_value=relay_config,
        ),
        patch.dict(
            "sys.modules",
            {
                "better_telegram_mcp.backends.bot_backend": type(
                    "module", (), {"BotBackend": MagicMock(return_value=mock_bot)}
                )()
            },
        ),
    ):
        async with _lifespan(mcp):
            assert srv._backend is mock_bot
            mock_bot.connect.assert_awaited_once()

        mock_bot.disconnect.assert_awaited_once()
        mock_settings_cls.from_relay_config.assert_called_once_with(relay_config)


@pytest.mark.asyncio
async def test_lifespan_falls_back_to_unconfigured_when_relay_fails():
    """Lifespan should fall back to unconfigured state when relay fails."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.server import _lifespan, mcp

    with (
        patch.object(srv, "Settings", return_value=MagicMock(is_configured=False)),
        patch(
            "better_telegram_mcp.relay_setup.ensure_config",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        async with _lifespan(mcp):
            assert srv._unconfigured is True

        assert srv._unconfigured is False


# --- relay_schema ---


def test_relay_schema_structure():
    """Verify relay schema has correct structure."""
    from better_telegram_mcp.relay_schema import RELAY_SCHEMA

    assert RELAY_SCHEMA["server"] == "better-telegram-mcp"
    assert RELAY_SCHEMA["displayName"] == "Telegram MCP"
    assert len(RELAY_SCHEMA["modes"]) == 2

    bot_mode = RELAY_SCHEMA["modes"][0]
    assert bot_mode["id"] == "bot"
    assert len(bot_mode["fields"]) == 1
    assert bot_mode["fields"][0]["key"] == "TELEGRAM_BOT_TOKEN"

    user_mode = RELAY_SCHEMA["modes"][1]
    assert user_mode["id"] == "user"
    assert len(user_mode["fields"]) == 3
    keys = [f["key"] for f in user_mode["fields"]]
    assert keys == ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_PHONE"]
