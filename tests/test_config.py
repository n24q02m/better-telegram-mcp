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
    s = Settings()
    assert s.mode == "user"


def test_user_mode_priority_over_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC")
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abcdef123456")
    s = Settings()
    assert s.mode == "user"


def test_explicit_mode_user(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MODE", "user")
    s = Settings()
    assert s.mode == "user"


def test_explicit_mode_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MODE", "bot")
    s = Settings()
    assert s.mode == "bot"


def test_invalid_mode_raises_error(monkeypatch):
    import pydantic
    import pytest

    monkeypatch.setenv("TELEGRAM_MODE", "invalid")
    with pytest.raises(pydantic.ValidationError):
        Settings()


def test_explicit_mode_overridden_by_credentials(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MODE", "bot")
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abcdef123456")
    s = Settings()
    assert s.mode == "bot"  # Explicit mode is respected, overriding credentials


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
    s = Settings()
    assert s.is_configured is True


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
