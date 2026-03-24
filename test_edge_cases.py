import json
from better_telegram_mcp.utils.formatting import safe_error

class CustomValueError(ValueError):
    pass

class CustomException(Exception):
    pass

def test_empty_message():
    e = ValueError()
    res = json.loads(safe_error(e))
    print("Empty ValueError:", res)

def test_multiple_args():
    e = ValueError("arg1", "arg2")
    res = json.loads(safe_error(e))
    print("Multiple args ValueError:", res)

def test_custom_subclass():
    e = CustomValueError("custom msg")
    res = json.loads(safe_error(e))
    print("CustomValueError:", res)

def test_custom_generic():
    e = CustomException("generic custom")
    res = json.loads(safe_error(e))
    print("CustomException:", res)

test_empty_message()
test_multiple_args()
test_custom_subclass()
test_custom_generic()
