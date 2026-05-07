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


def test_secret_priority_env_credential(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET", "env-cred")
    monkeypatch.setenv("DCR_SERVER_SECRET", "env-dcr")
    monkeypatch.setenv("MASTER_SECRET", "env-master")
    s = Settings()
    assert s.secret == "env-cred"


def test_secret_priority_env_dcr(monkeypatch):
    monkeypatch.delenv("CREDENTIAL_SECRET", raising=False)
    monkeypatch.setenv("DCR_SERVER_SECRET", "env-dcr")
    monkeypatch.setenv("MASTER_SECRET", "env-master")
    s = Settings()
    assert s.secret == "env-dcr"


def test_secret_persistence(tmp_path):
    # Test that it generates and persists a secret when no env vars are set
    import os

    for env in ["CREDENTIAL_SECRET", "DCR_SERVER_SECRET", "MASTER_SECRET"]:
        if env in os.environ:
            del os.environ[env]

    s = Settings(data_dir=tmp_path)
    secret1 = s.secret
    assert len(secret1) == 64  # urandom(32).hex()

    # Reload settings with same data_dir
    s2 = Settings(data_dir=tmp_path)
    assert s2.secret == secret1

# --- Settings.from_relay_config ---


def test_from_relay_config_bot_mode():
    """Create Settings from relay config with bot token."""
    config = {"TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"}
    s = Settings.from_relay_config(config)
    assert s.bot_token == "123456:ABC-DEF"
    assert s.mode == "bot"
    assert s.is_configured is True


def test_from_relay_config_user_mode():
    """Create Settings from relay config with user credentials."""
    config = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdef123456",
        "TELEGRAM_PHONE": "+84912345678",
    }
    s = Settings.from_relay_config(config)
    assert s.api_id == 12345
    assert s.api_hash == "abcdef123456"
    assert s.phone == "+84912345678"
    assert s.mode == "user"
    assert s.is_configured is True


def test_from_relay_config_empty_values():
    """Empty values in relay config should result in unconfigured state."""
    config = {"TELEGRAM_BOT_TOKEN": ""}
    s = Settings.from_relay_config(config)
    assert s.bot_token is None  # _empty_to_none normalizes it
    assert s.is_configured is False


def test_from_relay_config_missing_keys():
    """Missing keys should use built-in defaults for api_id/api_hash."""
    config = {}
    s = Settings.from_relay_config(config)
    assert s.bot_token is None
    assert s.api_id == 37984984  # built-in default
    assert s.api_hash == "2f5f4c76c4de7c07302380c788390100"  # built-in default
    assert s.is_configured is False  # no phone, no bot_token
