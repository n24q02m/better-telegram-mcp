"""Unit tests for utility functions in auth_server.py."""

from __future__ import annotations

from better_telegram_mcp.auth_server import _mask_phone, _sanitize_error


class TestSanitizeError:
    def test_phone_number_invalid(self):
        assert _sanitize_error("PHONE_NUMBER_INVALID") == "Invalid phone number format"

    def test_phone_code_invalid_exact(self):
        assert _sanitize_error("PHONE_CODE_INVALID") == "Invalid verification code"

    def test_password_required(self):
        assert _sanitize_error("Password is required for this account") == (
            "Two-factor authentication password is required."
        )

    def test_password_invalid(self):
        assert _sanitize_error("The password is invalid") == (
            "Incorrect 2FA password. Please try again."
        )

    def test_phone_code_invalid_pattern(self):
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

    def test_strips_caused_by_suffix(self):
        result = _sanitize_error("Something happened (caused by SomeError)")
        assert result == "Something happened"

    def test_passthrough_unknown_error(self):
        assert _sanitize_error("Some unknown error") == "Some unknown error"


class TestMaskPhone:
    def test_mask_long_phone(self):
        # length > 7: first 4 and last 4 preserved
        assert _mask_phone("+84912345678") == "+849***5678"

    def test_mask_short_phone(self):
        # length <= 7: first 2 preserved
        assert _mask_phone("1234567") == "12***"
        assert _mask_phone("123") == "12***"
