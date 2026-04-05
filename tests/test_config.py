from __future__ import annotations

from better_telegram_mcp.config import Settings


def test_bot_mode_detection(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF")
    s = Settings()
    assert s.mode == "bot"
    assert s.bot_token == "123456:ABC-DEF"


def test_user_mode_detection(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abcdef123456")
    monkeypatch.setenv("TELEGRAM_PHONE", "+84912345678")
    s = Settings()
    assert s.mode == "user"


def test_user_mode_priority_over_bot(monkeypatch):
    """When both bot_token and user credentials are set, bot_token takes priority."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC")
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abcdef123456")
    monkeypatch.setenv("TELEGRAM_PHONE", "+84912345678")
    s = Settings()
    assert s.mode == "bot"


def test_no_credentials_starts_unconfigured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    s = Settings()
    assert s.is_configured is False
    assert s.mode == "bot"  # default mode


def test_is_configured_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC")
    s = Settings()
    assert s.is_configured is True


def test_is_configured_user(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abcdef123456")
    monkeypatch.setenv("TELEGRAM_PHONE", "+84912345678")
    s = Settings()
    assert s.is_configured is True


def test_api_id_api_hash_without_phone_not_configured(monkeypatch):
    """api_id + api_hash without phone should NOT be configured (defaults exist)."""
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abcdef123456")
    s = Settings()
    assert s.is_configured is False
    assert s.mode == "bot"


def test_default_api_credentials():
    """api_id and api_hash have built-in defaults."""
    s = Settings()
    assert s.api_id == 37984984
    assert s.api_hash == "2f5f4c76c4de7c07302380c788390100"


def test_default_data_dir(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC")
    s = Settings()
    assert str(s.data_dir).endswith(".better-telegram-mcp")


def test_custom_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC")
    monkeypatch.setenv("TELEGRAM_DATA_DIR", str(tmp_path))
    s = Settings()
    assert s.data_dir == tmp_path


def test_session_path(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC")
    s = Settings()
    assert str(s.session_path).endswith("default.session")


def test_empty_to_none():
    from better_telegram_mcp.config import _empty_to_none

    assert _empty_to_none(None) is None
    assert _empty_to_none("") is None
    assert _empty_to_none("   ") is None
    assert _empty_to_none("valid") == "valid"
    assert _empty_to_none("  valid  ") == "  valid  "


def test_settings_with_empty_strings(monkeypatch):
    """Verify that whitespace-only env vars are normalized to None and don't trigger configured state."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "  ")
    monkeypatch.setenv("TELEGRAM_API_HASH", "")
    monkeypatch.setenv("TELEGRAM_PHONE", "")
    s = Settings()
    assert s.bot_token is None
    assert s.api_hash is None
    assert s.phone is None
    assert s.is_configured is False
    assert s.mode == "bot"


def test_from_relay_config_full():
    """Verify initialization with all keys provided."""
    config = {
        "TELEGRAM_BOT_TOKEN": "123:ABC",
        "TELEGRAM_PHONE": "+1234567890",
        "TELEGRAM_API_ID": "999",
        "TELEGRAM_API_HASH": "hash123",
    }
    s = Settings.from_relay_config(config)
    assert s.bot_token == "123:ABC"
    assert s.phone == "+1234567890"
    assert s.api_id == 999
    assert s.api_hash == "hash123"


def test_from_relay_config_partial():
    """Verify initialization with only some keys provided, ensuring defaults are respected."""
    config = {
        "TELEGRAM_PHONE": "+1234567890",
    }
    s = Settings.from_relay_config(config)
    assert s.bot_token is None
    assert s.phone == "+1234567890"
    # Defaults from Settings class
    assert s.api_id == 37984984
    assert s.api_hash == "2f5f4c76c4de7c07302380c788390100"
