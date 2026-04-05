from __future__ import annotations

import pytest

from better_telegram_mcp.backends.base import ModeError, TelegramBackend


def test_ensure_mode_passes_correct_mode(mock_backend):
    """Should not raise if the mode matches."""
    mock_backend.ensure_mode("bot")


def test_ensure_mode_fails_wrong_mode(mock_backend):
    """Should raise ModeError if the mode does not match."""
    with pytest.raises(ModeError, match="requires user mode"):
        mock_backend.ensure_mode("user")


def test_ensure_mode_user_passes(mock_user_backend):
    """Should not raise if the mode matches (user mode)."""
    mock_user_backend.ensure_mode("user")


def test_ensure_mode_user_fails(mock_user_backend):
    """Should raise ModeError if the mode does not match (expecting bot in user mode)."""
    with pytest.raises(ModeError, match="requires bot mode"):
        mock_user_backend.ensure_mode("bot")


def test_mode_error_message():
    """Verify the error message for user mode requirements."""
    err = ModeError("user")
    assert "TELEGRAM_API_ID" in str(err)
    assert "TELEGRAM_PHONE" in str(err)
    assert err.required_mode == "user"


def test_mode_error_non_user():
    """Verify the generic error message for other modes."""
    err = ModeError("bot")
    assert "requires bot mode" in str(err)
    assert err.required_mode == "bot"


def test_mode_error_custom_mode():
    """Verify the generic error message for a custom mode."""
    err = ModeError("custom")
    assert "requires custom mode" in str(err)
    assert err.required_mode == "custom"


def test_telegram_backend_is_abc():
    """TelegramBackend is an ABC and cannot be instantiated."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class TelegramBackend"):
        TelegramBackend("bot")


def test_telegram_backend_mode_initialization(mock_backend):
    """Verify that the mode attribute is correctly set."""
    assert mock_backend.mode == "bot"
