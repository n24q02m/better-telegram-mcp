import json
from datetime import datetime

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.backends.security import SecurityError
from better_telegram_mcp.utils.formatting import err, escape_html, ok, safe_error


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


def test_ok_edge_cases():
    assert ok(None) == "null"
    assert ok([]) == "[]"
    assert ok({}) == "{}"


def test_ok_collections():
    # set is not JSON serializable, should use str() via default=str
    data = {"s": {1, 2, 3}}
    result = ok(data)
    parsed = json.loads(result)
    # set str representation contains 1, 2, 3 and is wrapped in {}
    assert isinstance(parsed["s"], str)
    assert "1" in parsed["s"]
    assert "2" in parsed["s"]
    assert "3" in parsed["s"]
    assert parsed["s"].startswith("{")
    assert parsed["s"].endswith("}")


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


def test_err_non_string_input():
    # err() expects a str, but json.dumps handles other types too
    result = err(123)
    assert json.loads(result) == {"error": 123}


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


def test_safe_error_empty_message():
    # Allowed exception with empty message
    exc = ValueError("")
    result = safe_error(exc)
    assert json.loads(result) == {"error": ""}

    # Generic exception with empty message
    exc = Exception("")
    result = safe_error(exc)
    assert json.loads(result) == {
        "error": "Exception: Operation failed. Check server logs for details."
    }


def test_safe_error_subclasses_allowed():
    class CustomValueError(ValueError):
        pass

    exc = CustomValueError("custom message")
    result = safe_error(exc)
    assert json.loads(result) == {"error": "custom message"}


def test_safe_error_disallowed_oserror():
    # PermissionError is an OSError but not FileNotFoundError
    exc = PermissionError("access denied")
    result = safe_error(exc)
    parsed = json.loads(result)
    assert (
        parsed["error"]
        == "PermissionError: Operation failed. Check server logs for details."
    )
    assert "access denied" not in result


def test_safe_error_base_exception():
    # Although the type hint says Exception, in practice someone might pass BaseException
    # safe_error should still handle it if it makes it through
    exc = KeyboardInterrupt("stop")
    # KeyboardInterrupt is NOT a subclass of Exception, it's a sibling.
    # The code uses isinstance(e, (...)) and it doesn't match, so it falls through.
    result = safe_error(exc)
    parsed = json.loads(result)
    assert (
        parsed["error"]
        == "KeyboardInterrupt: Operation failed. Check server logs for details."
    )
    assert "stop" not in result


def test_ok_nested_mixed_types():
    data = {
        "str": "text",
        "nested": {"val": 1, "exc": ValueError("nested error")},
        "list": [1, {"a": 1}],
    }
    result = ok(data)
    parsed = json.loads(result)
    assert parsed["str"] == "text"
    assert parsed["nested"]["val"] == 1
    assert parsed["nested"]["exc"] == "nested error"
    assert parsed["list"][0] == 1
    assert parsed["list"][1]["a"] == 1


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("plain text", "plain text"),
        ("Hello <world>", "Hello &lt;world&gt;"),
        ("Keep & Calm", "Keep &amp; Calm"),
        ("Quotes \"and\" 'more'", "Quotes &quot;and&quot; &#x27;more&#x27;"),
        (None, "None"),
        ("", ""),
        (123, "123"),
        ({"key": "value"}, "{&#x27;key&#x27;: &#x27;value&#x27;}"),
        ([1, 2, "<"], "[1, 2, &#x27;&lt;&#x27;]"),
        ("😊", "😊"),
    ],
)
def test_escape_html(input_val, expected):
    assert escape_html(input_val) == expected
