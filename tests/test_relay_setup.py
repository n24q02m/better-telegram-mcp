"""Tests for relay setup integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.config import Settings
from better_telegram_mcp.relay_setup import (
    _is_user_mode_config,
    _needs_2fa_password,
    _sanitize_error,
)

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


# --- Lifespan integration ---


@pytest.mark.asyncio
async def test_lifespan_tries_credential_state_when_unconfigured():
    """Lifespan should use resolve_credential_state when no env vars are set."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import _lifespan, mcp

    mock_bot = AsyncMock()
    mock_bot.is_authorized = AsyncMock(return_value=True)

    # First Settings() returns unconfigured, second (after resolve) returns configured
    unconfigured_settings = MagicMock(is_configured=False)
    configured_settings = MagicMock(
        is_configured=True,
        mode="bot",
        bot_token="relay:TOKEN",
    )

    call_count = 0

    def settings_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return unconfigured_settings if call_count == 1 else configured_settings

    def mock_resolve():
        return CredentialState.CONFIGURED

    with (
        patch.object(srv, "Settings", side_effect=settings_factory),
        patch(
            "better_telegram_mcp.credential_state.resolve_credential_state",
            side_effect=mock_resolve,
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


@pytest.mark.asyncio
async def test_lifespan_falls_back_to_unconfigured_when_no_credentials():
    """Lifespan should fall back to unconfigured state when no credentials found."""
    import better_telegram_mcp.server as srv
    from better_telegram_mcp.credential_state import CredentialState
    from better_telegram_mcp.server import _lifespan, mcp

    def mock_resolve():
        return CredentialState.AWAITING_SETUP

    with (
        patch.object(srv, "Settings", return_value=MagicMock(is_configured=False)),
        patch(
            "better_telegram_mcp.credential_state.resolve_credential_state",
            side_effect=mock_resolve,
        ),
    ):
        async with _lifespan(mcp):
            assert srv._unconfigured is True

        assert srv._unconfigured is False


# --- relay_schema ---


def test_relay_schema_structure():
    """Verify relay schema has correct structure (flat fields for local OAuth form)."""
    from better_telegram_mcp.relay_schema import RELAY_SCHEMA, RELAY_SCHEMA_MODES

    # Flat schema for local OAuth form
    assert RELAY_SCHEMA["server"] == "better-telegram-mcp"
    assert RELAY_SCHEMA["displayName"] == "Telegram MCP"
    keys = [f["key"] for f in RELAY_SCHEMA["fields"]]
    assert "TELEGRAM_BOT_TOKEN" in keys
    assert "TELEGRAM_PHONE" in keys

    # Modes schema for relay page (backward compat)
    assert len(RELAY_SCHEMA_MODES["modes"]) == 2
    assert RELAY_SCHEMA_MODES["modes"][0]["id"] == "bot"
    assert RELAY_SCHEMA_MODES["modes"][1]["id"] == "user"


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
    def test_password_keyword(self):
        assert _needs_2fa_password("SessionPasswordNeeded") is True

    def test_2fa_keyword(self):
        assert _needs_2fa_password("2fa authentication required") is True

    def test_two_factor_keyword(self):
        assert _needs_2fa_password("Two-factor auth needed") is True

    def test_srp_keyword(self):
        assert _needs_2fa_password("SRP protocol required") is True

    def test_no_match(self):
        assert _needs_2fa_password("Invalid phone number") is False


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
