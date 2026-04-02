from better_telegram_mcp.relay_setup import _is_user_mode_config


def test_is_user_mode_config_phone_only():
    assert _is_user_mode_config({"TELEGRAM_PHONE": "+1234567890"}) is True


def test_is_user_mode_config_api_creds_only():
    assert (
        _is_user_mode_config(
            {"TELEGRAM_API_ID": "12345", "TELEGRAM_API_HASH": "hash123"}
        )
        is True
    )


def test_is_user_mode_config_all_user_fields():
    assert (
        _is_user_mode_config(
            {
                "TELEGRAM_PHONE": "+1234567890",
                "TELEGRAM_API_ID": "12345",
                "TELEGRAM_API_HASH": "hash123",
            }
        )
        is True
    )


def test_is_user_mode_config_empty_phone():
    assert _is_user_mode_config({"TELEGRAM_PHONE": ""}) is False


def test_is_user_mode_config_partial_api_id():
    assert _is_user_mode_config({"TELEGRAM_API_ID": "12345"}) is False


def test_is_user_mode_config_partial_api_hash():
    assert _is_user_mode_config({"TELEGRAM_API_HASH": "hash123"}) is False


def test_is_user_mode_config_bot_mode():
    assert _is_user_mode_config({"TELEGRAM_BOT_TOKEN": "bot:token"}) is False


def test_is_user_mode_config_empty_dict():
    assert _is_user_mode_config({}) is False


def test_is_user_mode_config_random_fields():
    assert _is_user_mode_config({"OTHER_FIELD": "value"}) is False
