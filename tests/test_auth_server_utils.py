from better_telegram_mcp.auth_server import _mask_phone, _sanitize_error


def test_sanitize_error_simple():
    assert (
        _sanitize_error("PHONE_CODE_INVALID")
        == "Invalid OTP code. Please check and try again."
    )
    assert (
        _sanitize_error("The phone code is invalid")
        == "Invalid OTP code. Please check and try again."
    )
    assert _sanitize_error("PHONE_NUMBER_INVALID") == "Invalid phone number format"
    assert (
        _sanitize_error("FLOOD_WAIT_300")
        == "Too many attempts. Please wait a moment and try again."
    )


def test_sanitize_error_caused_by():
    assert (
        _sanitize_error("PHONE_CODE_INVALID (caused by SignInRequest)")
        == "Invalid OTP code. Please check and try again."
    )
    assert _sanitize_error("Unknown error (caused by SomeRequest)") == "Unknown error"


def test_sanitize_error_unknown():
    assert _sanitize_error("Some weird telegram error") == "Some weird telegram error"


def test_mask_phone():
    # Length > 7: phone[:4] + "***" + phone[-4:]
    assert _mask_phone("+1234567890") == "+123***7890"
    assert _mask_phone("12345678") == "1234***5678"

    # Length <= 7: phone[:2] + "***"
    assert _mask_phone("1234567") == "12***"
    assert _mask_phone("123") == "12***"
    assert _mask_phone("1") == "1***"
