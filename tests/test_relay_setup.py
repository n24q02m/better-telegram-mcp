"""Tests for relay setup integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings
from better_telegram_mcp.relay_setup import (
    _is_user_mode_config,
    _needs_2fa_password,
    _relay_telethon_auth,
    _sanitize_error,
)

# --- Settings.from_relay_config ---


@pytest.mark.asyncio
async def test_relay_telethon_auth_success():
    from better_telegram_mcp.relay_setup import _relay_telethon_auth

    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.phone = "+1234567890"

    with (
        patch("mcp_relay_core.relay.client.send_message", new_callable=AsyncMock),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses", new_callable=AsyncMock
        ) as mock_poll,
    ):
        # User provides code
        mock_poll.return_value = "12345"
        mock_backend.sign_in.return_value = {"authenticated_as": "Test User"}

        result = await _relay_telethon_auth(
            "http://relay", "123", mock_backend, mock_settings
        )

        assert result is True
        mock_backend.send_code.assert_awaited_once_with("+1234567890")
        mock_backend.sign_in.assert_awaited_once_with("+1234567890", "12345")


@pytest.mark.asyncio
async def test_relay_telethon_auth_2fa():
    from better_telegram_mcp.relay_setup import _relay_telethon_auth

    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.phone = "+1234567890"

    with (
        patch("mcp_relay_core.relay.client.send_message", new_callable=AsyncMock),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses", new_callable=AsyncMock
        ) as mock_poll,
    ):
        # 1st response: code. 2nd response: 2FA password
        mock_poll.side_effect = ["12345", "mypassword"]

        # 1st sign in raises SessionPasswordNeededError
        def mock_sign_in(phone, code, password=None):
            if not password:
                raise Exception(
                    "Two-step verification is enabled. A password is required."
                )
            return {"authenticated_as": "Test User"}

        mock_backend.sign_in.side_effect = mock_sign_in

        result = await _relay_telethon_auth(
            "http://relay", "123", mock_backend, mock_settings
        )

        assert result is True
        mock_backend.send_code.assert_awaited_once_with("+1234567890")
        assert mock_backend.sign_in.call_count == 2


@pytest.mark.asyncio
async def test_relay_telethon_auth_no_phone():
    from better_telegram_mcp.relay_setup import _relay_telethon_auth

    mock_backend = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.phone = None

    with patch(
        "mcp_relay_core.relay.client.send_message", new_callable=AsyncMock
    ) as mock_send:
        result = await _relay_telethon_auth(
            "http://relay", "123", mock_backend, mock_settings
        )
        assert result is False
        mock_send.assert_awaited_once()


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
    """Missing keys should use built-in defaults for api_id/api_hash."""
    config = {}
    s = Settings.from_relay_config(config)
    assert s.bot_token is None
    assert s.api_id == 37984984  # built-in default
    assert s.api_hash == "2f5f4c76c4de7c07302380c788390100"  # built-in default
    assert s.is_configured is False  # no phone, no bot_token


# --- check_saved_sessions ---


def test_check_saved_sessions_no_dir(tmp_path):
    """Returns False when data directory does not exist."""
    from better_telegram_mcp.relay_setup import check_saved_sessions

    with patch(
        "better_telegram_mcp.relay_setup.Path.home",
        return_value=tmp_path / "nonexistent",
    ):
        assert check_saved_sessions() is False


def test_check_saved_sessions_empty_dir(tmp_path):
    """Returns False when data directory exists but has no session files."""
    from better_telegram_mcp.relay_setup import check_saved_sessions

    data_dir = tmp_path / ".better-telegram-mcp"
    data_dir.mkdir()

    with patch(
        "better_telegram_mcp.relay_setup.Path.home",
        return_value=tmp_path,
    ):
        assert check_saved_sessions() is False


def test_check_saved_sessions_with_sessions(tmp_path):
    """Returns True when session files exist."""
    from better_telegram_mcp.relay_setup import check_saved_sessions

    data_dir = tmp_path / ".better-telegram-mcp"
    data_dir.mkdir()
    (data_dir / "user.session").write_text("session_data")

    with patch(
        "better_telegram_mcp.relay_setup.Path.home",
        return_value=tmp_path,
    ):
        assert check_saved_sessions() is True


# --- ensure_config ---


@pytest.mark.asyncio
async def test_ensure_config_returns_config_file_data():
    """ensure_config returns data from config file when available."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result = MagicMock()
    mock_result.config = {"TELEGRAM_BOT_TOKEN": "from-file:TOKEN"}
    mock_result.source = "file"

    with patch(
        "mcp_relay_core.storage.resolver.resolve_config",
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
        "mcp_relay_core.storage.resolver.resolve_config",
        side_effect=[mock_result_none, mock_result_user],
    ):
        result = await ensure_config()

    assert result is not None
    assert result["TELEGRAM_API_ID"] == "12345"


@pytest.mark.asyncio
async def test_ensure_config_returns_none_on_saved_sessions():
    """ensure_config returns None when saved sessions exist (no relay needed)."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=True,
        ),
    ):
        result = await ensure_config()

    assert result is None


@pytest.mark.asyncio
async def test_ensure_config_triggers_relay_when_nothing_found():
    """ensure_config triggers relay setup when no config found anywhere."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"
    mock_session.session_id = "abc123"

    expected_config = {"TELEGRAM_BOT_TOKEN": "relay:TOKEN"}

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=expected_config,
        ),
        patch(
            "mcp_relay_core.storage.config_file.write_config",
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
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
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
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Relay setup timed out"),
        ),
    ):
        result = await ensure_config()

    assert result is None


@pytest.mark.asyncio
async def test_ensure_config_returns_none_on_relay_skipped():
    """ensure_config returns None when user skips relay setup."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            side_effect=RuntimeError("RELAY_SKIPPED by user"),
        ),
    ):
        result = await ensure_config()

    assert result is None


@pytest.mark.asyncio
async def test_ensure_config_returns_none_on_relay_error():
    """ensure_config returns None on unexpected relay RuntimeError."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Some other relay error"),
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
    assert (
        len(user_mode["fields"]) == 1
    )  # Only phone (API_ID/HASH have built-in defaults)
    keys = [f["key"] for f in user_mode["fields"]]
    assert keys == ["TELEGRAM_PHONE"]


# --- _sanitize_error ---


class TestSanitizeError:
    def test_password_required(self):
        assert _sanitize_error("Password is required for this account") == (
            "Two-factor authentication password is required."
        )

    def test_password_invalid(self):
        assert _sanitize_error("The password is invalid") == (
            "Incorrect 2FA password. Please try again."
        )

    def test_invalid_password(self):
        assert _sanitize_error("Invalid password provided") == (
            "Incorrect 2FA password. Please try again."
        )

    def test_phone_code_invalid(self):
        assert _sanitize_error("Phone code is invalid") == (
            "Invalid OTP code. Please check and try again."
        )

    def test_code_expired(self):
        assert _sanitize_error("Phone code has expired") == (
            "OTP code has expired. Please request a new one."
        )

    def test_flood_wait(self):
        assert _sanitize_error("Flood wait of 300 seconds") == (
            "Too many attempts. Please wait a moment and try again."
        )

    def test_too_many(self):
        assert _sanitize_error("Too many requests") == (
            "Too many attempts. Please wait a moment and try again."
        )

    def test_strips_caused_by_suffix(self):
        result = _sanitize_error("Something happened (caused by SomeError)")
        assert result == "Something happened"

    def test_passthrough_unknown_error(self):
        assert _sanitize_error("Some unknown error") == "Some unknown error"


# --- _needs_2fa_password ---


class TestNeeds2faPassword:
    def test_session_password_needed(self):
        assert _needs_2fa_password("SessionPasswordNeeded") is True

    def test_password_required(self):
        assert _needs_2fa_password("password required") is True

    def test_2fa_password(self):
        assert _needs_2fa_password("2fa password") is True

    def test_two_factor_keyword(self):
        assert _needs_2fa_password("Two-factor auth needed") is True

    def test_srp_keyword(self):
        assert _needs_2fa_password("SRP protocol required") is True

    def test_mixed_case(self):
        assert _needs_2fa_password("TwO-FaCtOr needed") is True
        assert _needs_2fa_password("PASSWORD REQUIRED") is True

    def test_no_match_just_password(self):
        assert _needs_2fa_password("incorrect password") is False

    def test_no_match_random(self):
        assert _needs_2fa_password("Invalid phone number") is False
        assert _needs_2fa_password("") is False
        assert _needs_2fa_password("error 123") is False

    def test_no_match_just_2fa(self):
        # 2fa without password should not match unless it's two-factor/srp
        assert _needs_2fa_password("2fa error") is False


# --- _is_user_mode_config ---


class TestIsUserModeConfig:
    def test_phone_present(self):
        config = {"TELEGRAM_PHONE": "+84912345678"}
        assert _is_user_mode_config(config) is True

    def test_full_user_config_with_phone(self):
        config = {
            "TELEGRAM_API_ID": "123",
            "TELEGRAM_API_HASH": "abc",
            "TELEGRAM_PHONE": "+84912345678",
        }
        assert _is_user_mode_config(config) is True

    def test_missing_phone(self):
        config = {"TELEGRAM_API_ID": "123", "TELEGRAM_API_HASH": "abc"}
        assert _is_user_mode_config(config) is False

    def test_bot_config(self):
        config = {"TELEGRAM_BOT_TOKEN": "123:ABC"}
        assert _is_user_mode_config(config) is False

    def test_empty_phone(self):
        config = {"TELEGRAM_PHONE": ""}
        assert _is_user_mode_config(config) is False


# --- _relay_telethon_auth ---


@pytest.mark.asyncio
async def test_relay_auth_no_phone():
    """Returns False and sends error when phone is missing."""
    mock_backend = AsyncMock()
    settings = MagicMock()
    settings.phone = None

    with patch(
        "mcp_relay_core.relay.client.send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is False
    mock_send.assert_awaited_once()
    call_args = mock_send.call_args[0]
    assert call_args[2]["type"] == "error"
    assert "Phone number" in call_args[2]["text"]


@pytest.mark.asyncio
async def test_relay_auth_send_code_fails():
    """Returns False when send_code raises an exception."""
    mock_backend = AsyncMock()
    mock_backend.send_code.side_effect = Exception("Network error")
    settings = MagicMock()
    settings.phone = "+84912345678"

    with patch(
        "mcp_relay_core.relay.client.send_message",
        new_callable=AsyncMock,
    ) as mock_send:
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is False
    # Should send info + error messages
    assert mock_send.await_count == 2


@pytest.mark.asyncio
async def test_relay_auth_otp_timeout():
    """Returns False when OTP polling times out."""
    mock_backend = AsyncMock()
    settings = MagicMock()
    settings.phone = "+84912345678"

    with (
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Timed out"),
        ),
    ):
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is False


@pytest.mark.asyncio
async def test_relay_auth_sign_in_success():
    """Returns True when OTP sign-in succeeds on first try."""
    mock_backend = AsyncMock()
    mock_backend.sign_in.return_value = {"authenticated_as": "TestUser"}
    settings = MagicMock()
    settings.phone = "+84912345678"

    with (
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses",
            new_callable=AsyncMock,
            return_value="12345",
        ),
    ):
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is True
    mock_backend.sign_in.assert_awaited_once_with("+84912345678", "12345")


@pytest.mark.asyncio
async def test_relay_auth_sign_in_non_2fa_error():
    """Returns False when sign-in fails with a non-2FA error."""
    mock_backend = AsyncMock()
    mock_backend.sign_in.side_effect = Exception("Invalid phone number")
    settings = MagicMock()
    settings.phone = "+84912345678"

    with (
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses",
            new_callable=AsyncMock,
            return_value="12345",
        ),
    ):
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is False


@pytest.mark.asyncio
async def test_relay_auth_2fa_success():
    """Returns True when 2FA password sign-in succeeds."""
    mock_backend = AsyncMock()
    # First call raises 2FA error, second succeeds
    mock_backend.sign_in.side_effect = [
        Exception("SessionPasswordNeeded"),
        {"authenticated_as": "TestUser"},
    ]
    settings = MagicMock()
    settings.phone = "+84912345678"

    with (
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses",
            new_callable=AsyncMock,
            side_effect=["12345", "my2fapassword"],
        ),
    ):
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is True
    assert mock_backend.sign_in.await_count == 2


@pytest.mark.asyncio
async def test_relay_auth_2fa_timeout():
    """Returns False when 2FA password polling times out."""
    mock_backend = AsyncMock()
    mock_backend.sign_in.side_effect = Exception("SessionPasswordNeeded")
    settings = MagicMock()
    settings.phone = "+84912345678"

    with (
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses",
            new_callable=AsyncMock,
            side_effect=["12345", RuntimeError("Timed out")],
        ),
    ):
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is False


@pytest.mark.asyncio
async def test_relay_auth_2fa_sign_in_fails():
    """Returns False when 2FA sign-in fails."""
    mock_backend = AsyncMock()
    mock_backend.sign_in.side_effect = [
        Exception("SessionPasswordNeeded"),
        Exception("Incorrect 2FA password"),
    ]
    settings = MagicMock()
    settings.phone = "+84912345678"

    with (
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_responses",
            new_callable=AsyncMock,
            side_effect=["12345", "wrongpassword"],
        ),
    ):
        result = await _relay_telethon_auth(
            "http://relay", "session-1", mock_backend, settings
        )

    assert result is False


# --- ensure_config user mode + bot mode completion paths ---


@pytest.mark.asyncio
async def test_ensure_config_user_mode_triggers_telethon_auth():
    """ensure_config triggers Telethon auth for user mode config."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"
    mock_session.session_id = "abc123"

    user_config = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdef",
        "TELEGRAM_PHONE": "+84912345678",
    }

    mock_backend = AsyncMock()
    mock_backend.is_authorized.return_value = False

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=user_config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "better_telegram_mcp.relay_setup._relay_telethon_auth",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_auth,
        patch(
            "better_telegram_mcp.backends.user_backend.UserBackend",
            return_value=mock_backend,
        ),
    ):
        result = await ensure_config()

    assert result == user_config
    mock_auth.assert_awaited_once()
    mock_backend.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_config_user_mode_already_authorized():
    """ensure_config sends complete message when user is already authorized."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"
    mock_session.session_id = "abc123"

    user_config = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdef",
        "TELEGRAM_PHONE": "+84912345678",
    }

    mock_backend = AsyncMock()
    mock_backend.is_authorized.return_value = True

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=user_config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
        patch(
            "better_telegram_mcp.backends.user_backend.UserBackend",
            return_value=mock_backend,
        ),
    ):
        result = await ensure_config()

    assert result == user_config
    # Verify "complete" message was sent
    complete_call = mock_send.call_args_list[-1]
    assert complete_call[0][2]["type"] == "complete"
    assert "already authorized" in complete_call[0][2]["text"]
    mock_backend.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_config_bot_mode_sends_complete():
    """ensure_config sends complete message for bot mode config."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"
    mock_session.session_id = "abc123"

    bot_config = {"TELEGRAM_BOT_TOKEN": "relay:TOKEN"}

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=bot_config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        result = await ensure_config()

    assert result == bot_config
    # Verify "complete" message was sent for bot mode
    complete_call = mock_send.call_args_list[-1]
    assert complete_call[0][2]["type"] == "complete"
    assert "Setup complete" in complete_call[0][2]["text"]


@pytest.mark.asyncio
async def test_ensure_config_user_mode_auth_fails():
    """ensure_config still returns config when Telethon auth fails."""
    from better_telegram_mcp.relay_setup import ensure_config

    mock_result_none = MagicMock()
    mock_result_none.config = None
    mock_result_none.source = None

    mock_session = MagicMock()
    mock_session.relay_url = "https://example.com/setup?s=abc#k=key&p=pass"
    mock_session.session_id = "abc123"

    user_config = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdef",
        "TELEGRAM_PHONE": "+84912345678",
    }

    mock_backend = AsyncMock()
    mock_backend.is_authorized.return_value = False

    with (
        patch(
            "mcp_relay_core.storage.resolver.resolve_config",
            return_value=mock_result_none,
        ),
        patch(
            "better_telegram_mcp.relay_setup.check_saved_sessions",
            return_value=False,
        ),
        patch(
            "mcp_relay_core.relay.client.create_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ),
        patch(
            "mcp_relay_core.relay.client.poll_for_result",
            new_callable=AsyncMock,
            return_value=user_config,
        ),
        patch("mcp_relay_core.storage.config_file.write_config"),
        patch(
            "mcp_relay_core.relay.client.send_message",
            new_callable=AsyncMock,
            return_value="msg-1",
        ),
        patch(
            "better_telegram_mcp.relay_setup._relay_telethon_auth",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "better_telegram_mcp.backends.user_backend.UserBackend",
            return_value=mock_backend,
        ),
    ):
        result = await ensure_config()

    # Config is still returned even if auth fails (creds are saved)
    assert result == user_config
