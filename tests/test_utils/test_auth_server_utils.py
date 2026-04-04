import pytest

from better_telegram_mcp.auth_server import _mask_phone, _sanitize_error


@pytest.mark.parametrize(
    "msg, expected",
    [
        ("Some error (caused by ABC)", "Some error"),
        (
            "PHONE_NUMBER_INVALID",
            "Invalid phone number. Please check your TELEGRAM_PHONE.",
        ),
        (
            "The password is required for this session",
            "Two-factor authentication (2FA) is required. Please enter your password.",
        ),
        (
            "The 2fa is required here",
            "Two-factor authentication (2FA) is required. Please enter your password.",
        ),
        ("The password is invalid", "Invalid 2FA password. Please try again."),
        (
            "The code is invalid",
            "Invalid or expired OTP code. Please request a new one.",
        ),
        (
            "The code is expired",
            "Invalid or expired OTP code. Please request a new one.",
        ),
        ("FLOOD_WAIT_100", "Too many attempts. Please wait a moment and try again."),
        ("too many attempts", "Too many attempts. Please wait a moment and try again."),
        ("Something else", "Something else"),
    ],
)
def test_sanitize_error(msg, expected):
    assert _sanitize_error(msg) == expected


@pytest.mark.parametrize(
    "phone, expected",
    [
        ("", "***"),
        ("1", "1***"),
        ("12", "12***"),
        ("123", "12***"),
        ("1234567", "12***"),
        ("12345678", "1234***5678"),
        ("+1234567890", "+123***7890"),
    ],
)
def test_mask_phone(phone, expected):
    assert _mask_phone(phone) == expected
