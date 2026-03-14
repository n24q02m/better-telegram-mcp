from __future__ import annotations

import pytest
from pydantic import ValidationError

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


def test_no_credentials_error(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    with pytest.raises(ValidationError):
        Settings()


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
