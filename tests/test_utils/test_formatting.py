import json
from datetime import datetime

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.security import SecurityError
from better_telegram_mcp.utils.formatting import (
    err,
    mask_phone,
    ok,
    safe_error,
    sanitize_error,
)


def test_ok_basic_serialization():
    data = {"key": "value", "number": 42}
    result = ok(data)
    assert result == '{"key": "value", "number": 42}'
    assert json.loads(result) == data


def test_ok_unicode_handling():
    data = {"emoji": "😊", "cyrillic": "Привет", "chinese": "你好"}
    result = ok(data)
    # Ensure Unicode characters are NOT escaped (ensure_ascii=False)
    assert "😊" in result
    assert "Привет" in result
    assert "你好" in result
    assert json.loads(result) == data


def test_ok_unserializable_objects():
    # Objects that aren't natively JSON serializable should fallback to str
    class CustomObject:
        def __str__(self):
            return "CustomObjectString"

    dt = datetime(2024, 1, 1, 12, 0, 0)
    data = {"date": dt, "custom": CustomObject()}

    result = ok(data)
    assert '"date": "2024-01-01 12:00:00"' in result
    assert '"custom": "CustomObjectString"' in result

    parsed = json.loads(result)
    assert parsed["date"] == "2024-01-01 12:00:00"
    assert parsed["custom"] == "CustomObjectString"


def test_err_basic_serialization():
    message = "Something went wrong"
    result = err(message)
    assert result == '{"error": "Something went wrong"}'

    parsed = json.loads(result)
    assert parsed["error"] == message


def test_err_unicode_handling():
    message = "Ошибка: ❌"
    result = err(message)
    # Ensure Unicode characters are NOT escaped
    assert "Ошибка: ❌" in result

    parsed = json.loads(result)
    assert parsed["error"] == message


def test_err_special_characters():
    # Test strings with special JSON characters
    message = 'Line 1\nLine 2\tTabbed "Quoted" \\Backslash\\'
    result = err(message)

    parsed = json.loads(result)
    assert parsed["error"] == message


def test_err_empty_string():
    message = ""
    result = err(message)
    assert result == '{"error": ""}'

    parsed = json.loads(result)
    assert parsed["error"] == ""


def test_err_long_string():
    message = "a" * 1000
    result = err(message)

    parsed = json.loads(result)
    assert parsed["error"] == message


def test_safe_error_allowed_exceptions():
    # Exceptions that should expose their actual message
    allowed_exceptions = [
        (
            ModeError("user"),
            "This action requires user mode. Set TELEGRAM_API_ID + TELEGRAM_API_HASH + TELEGRAM_PHONE.",
        ),
        (ModeError("bot"), "This action requires bot mode."),
        (SecurityError("Security error message"), "Security error message"),
        (ValueError("Value error message"), "Value error message"),
        (FileNotFoundError("File not found message"), "File not found message"),
    ]

    for exc, expected_msg in allowed_exceptions:
        result = safe_error(exc)
        parsed = json.loads(result)
        assert parsed["error"] == expected_msg


def test_safe_error_generic_exceptions():
    # Exceptions that should be sanitized to avoid leaking internals
    generic_exceptions = [
        KeyError("internal_key"),
        TypeError("bad type"),
        RuntimeError("system crash"),
        Exception("generic fail"),
    ]

    for exc in generic_exceptions:
        result = safe_error(exc)
        parsed = json.loads(result)

        # Format should be: "{ExceptionName}: Operation failed. Check server logs for details."
        expected_msg = (
            f"{type(exc).__name__}: Operation failed. Check server logs for details."
        )
        assert parsed["error"] == expected_msg

        # Ensure internal details are NOT leaked
        assert str(exc) not in result


def test_mask_phone_variants():
    # Long phone (> 7 chars)
    assert mask_phone("1234567890") == "1234***7890"
    assert mask_phone("12345678") == "1234***5678"

    # Short phone (<= 7 chars)
    assert mask_phone("1234567") == "12***"
    assert mask_phone("12") == "12***"
    assert mask_phone("1") == "1***"
    assert mask_phone("") == "***"


def test_sanitize_error_variants():
    # Known simplifications
    assert (
        sanitize_error("password required")
        == "Two-factor authentication password is required."
    )
    assert (
        sanitize_error("PASSWORD REQUIRED")
        == "Two-factor authentication password is required."
    )
    assert (
        sanitize_error("invalid password")
        == "Incorrect 2FA password. Please try again."
    )
    assert (
        sanitize_error("phone code invalid")
        == "Invalid OTP code. Please check and try again."
    )
    assert (
        sanitize_error("phone code expired")
        == "OTP code has expired. Please request a new one."
    )
    assert (
        sanitize_error("flood wait 300")
        == "Too many attempts. Please wait a moment and try again."
    )

    # Caused by stripping
    assert sanitize_error("Internal error (caused by SomeRPCError)") == "Internal error"
    assert (
        sanitize_error("Already sanitized (caused by some_error) ")
        == "Already sanitized"
    )

    # Passthrough
    assert sanitize_error("Unknown random error") == "Unknown random error"
    assert sanitize_error("") == ""
