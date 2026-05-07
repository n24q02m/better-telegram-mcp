"""Tests for relay setup integration."""

from __future__ import annotations

from unittest.mock import patch

from better_telegram_mcp.relay_setup import (
    _is_user_mode_config,
    _needs_2fa_password,
    _sanitize_error,
)

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


def test_check_saved_sessions_os_error(tmp_path):
    """Returns False when an OSError (e.g., PermissionError) occurs."""
    from better_telegram_mcp.relay_setup import check_saved_sessions

    with patch(
        "better_telegram_mcp.relay_setup.Path.home",
        side_effect=OSError("Access denied"),
    ):
        assert check_saved_sessions() is False


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

    def test_complex_cases(self):
        """Verify _sanitize_error handles varied and combined error patterns."""
        assert (
            _sanitize_error("phone code is invalid (caused by some internal error)")
            == "Invalid OTP code. Please check and try again."
        )
        assert (
            _sanitize_error("TOO MANY REQUESTS (CAUSED BY FLOODWAIT)")
            == "Too many attempts. Please wait a moment and try again."
        )
        assert (
            _sanitize_error("  something something password required   ")
            == "Two-factor authentication password is required."
        )


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
