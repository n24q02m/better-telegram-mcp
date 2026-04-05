import json
from datetime import datetime

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.security import SecurityError
from better_telegram_mcp.utils.formatting import _mask_phone, err, ok, safe_error


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


def test_mask_phone_empty():
    assert _mask_phone("") == "***"


def test_mask_phone_very_short():
    assert _mask_phone("1") == "1***"
    assert _mask_phone("12") == "12***"


def test_mask_phone_boundary():
    # Exactly 7 characters
    assert _mask_phone("1234567") == "12***"
    # Exactly 8 characters
    assert _mask_phone("12345678") == "1234***5678"


def test_mask_phone_long():
    assert _mask_phone("1234567890") == "1234***7890"
    assert _mask_phone("+12345678901") == "+123***8901"
