import json
from datetime import datetime

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.security import SecurityError
from better_telegram_mcp.utils.formatting import err, ok, safe_error


def test_ok_basic_serialization():
    data = {"key": "value", "number": 42}
    result = ok(data)
    parsed = json.loads(result)

    assert parsed["status"] == "ok"
    assert parsed["ok"] is True
    assert parsed["data"] == data
    # Spreading check
    assert parsed["key"] == "value"
    assert parsed["number"] == 42


def test_ok_unicode_handling():
    data = {"emoji": "😊", "cyrillic": "Привет", "chinese": "你好"}
    result = ok(data)
    # Ensure Unicode characters are NOT escaped (ensure_ascii=False)
    assert "😊" in result
    assert "Привет" in result
    assert "你好" in result

    parsed = json.loads(result)
    assert parsed["status"] == "ok"
    assert parsed["ok"] is True
    assert parsed["data"] == data
    assert parsed["emoji"] == "😊"


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
    assert parsed["status"] == "ok"
    assert parsed["ok"] is True
    assert parsed["data"]["date"] == "2024-01-01 12:00:00"
    assert parsed["date"] == "2024-01-01 12:00:00"


def test_ok_edge_cases():
    # ok(None)
    result = ok(None)
    parsed = json.loads(result)
    assert parsed == {"status": "ok", "ok": True, "data": None}

    # ok([])
    result = ok([])
    parsed = json.loads(result)
    assert parsed == {"status": "ok", "ok": True, "data": []}

    # ok({})
    result = ok({})
    parsed = json.loads(result)
    assert parsed == {"status": "ok", "ok": True, "data": {}}


def test_ok_collections():
    # set is not JSON serializable, should use str() via default=str
    data = {"s": {1, 2, 3}}
    result = ok(data)
    parsed = json.loads(result)

    assert parsed["status"] == "ok"
    assert parsed["ok"] is True
    # set str representation contains 1, 2, 3 and is wrapped in {}
    assert isinstance(parsed["data"]["s"], str)
    assert "1" in parsed["data"]["s"]
    assert "2" in parsed["data"]["s"]
    assert "3" in parsed["data"]["s"]


def test_err_basic_serialization():
    message = "Something went wrong"
    result = err(message)
    parsed = json.loads(result)

    assert parsed["status"] == "error"
    assert parsed["message"] == message
    assert parsed["error"] == message


def test_err_unicode_handling():
    message = "Ошибка: ❌"
    result = err(message)
    # Ensure Unicode characters are NOT escaped
    assert "Ошибка: ❌" in result

    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["message"] == message


def test_err_non_string_input():
    # err() expects a str, but json.dumps handles other types too
    result = err(123)
    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["message"] == 123


def test_ok_status_prioritization():
    # If data contains a 'status' key, it should override the default 'ok'
    data = {"status": "already_configured", "detail": "test"}
    result = ok(data)
    parsed = json.loads(result)

    assert parsed["status"] == "already_configured"
    assert parsed["ok"] is True
    assert parsed["data"] == data
    assert parsed["detail"] == "test"


def test_ok_non_dict_data():
    # If data is not a dict, no spreading should occur
    result = ok("just a string")
    parsed = json.loads(result)
    assert parsed == {"status": "ok", "ok": True, "data": "just a string"}


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
        assert parsed["status"] == "error"
        assert parsed["message"] == expected_msg


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
        assert parsed["status"] == "error"

        expected_msg = (
            f"{type(exc).__name__}: Operation failed. Check server logs for details."
        )
        assert parsed["message"] == expected_msg


def test_ok_nested_mixed_types():
    data = {
        "str": "text",
        "nested": {"val": 1, "exc": ValueError("nested error")},
        "list": [1, {"a": 1}],
    }
    result = ok(data)
    parsed = json.loads(result)

    assert parsed["status"] == "ok"
    assert parsed["data"]["nested"]["exc"] == "nested error"
    assert parsed["nested"]["exc"] == "nested error"
