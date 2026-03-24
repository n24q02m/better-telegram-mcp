from __future__ import annotations

import pytest

from better_telegram_mcp.backends.base import ModeError


def test_ensure_mode_passes_correct_mode(mock_backend):
    mock_backend.ensure_mode("bot")


def test_ensure_mode_fails_wrong_mode(mock_backend):
    with pytest.raises(ModeError, match="requires user mode"):
        mock_backend.ensure_mode("user")


def test_mode_error_message():
    err = ModeError("user")
    assert "TELEGRAM_API_ID" in str(err)
    assert "TELEGRAM_PHONE" in str(err)


def test_mode_error_non_user():
    err = ModeError("bot")
    assert "requires bot mode" in str(err)


def test_ensure_mode_user_fails_bot_mode(mock_user_backend):
    with pytest.raises(ModeError, match="requires bot mode"):
        mock_user_backend.ensure_mode("bot")
