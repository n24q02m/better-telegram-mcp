from __future__ import annotations

import pytest

from better_telegram_mcp.backends.base import ModeError


def test_ensure_mode_passes_correct_mode(mock_backend):
    mock_backend.ensure_mode("bot")


def test_ensure_mode_fails_wrong_mode(mock_backend):
    # mock_backend defaults to "bot" mode in conftest.py
    with pytest.raises(
        ModeError, match="requires user mode, but server is in bot mode"
    ):
        mock_backend.ensure_mode("user")


def test_ensure_mode_fails_wrong_mode_user(mock_user_backend):
    # mock_user_backend defaults to "user" mode in conftest.py
    with pytest.raises(
        ModeError, match="requires bot mode, but server is in user mode"
    ):
        mock_user_backend.ensure_mode("bot")


def test_mode_error_is_value_error():
    err = ModeError("user", "bot")
    assert isinstance(err, ValueError)


def test_mode_error_message_with_current_mode():
    err = ModeError("user", "bot")
    assert "requires user mode, but server is in bot mode" in str(err)
    assert "TELEGRAM_API_ID" in str(err)


def test_mode_error_message_no_current_mode():
    err = ModeError("user")
    assert "This action requires user mode." in str(err)
    assert "TELEGRAM_API_ID" in str(err)


def test_mode_error_non_user_no_current_mode():
    err = ModeError("bot")
    assert "This action requires bot mode." in str(err)
