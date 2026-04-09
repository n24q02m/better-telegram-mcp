from __future__ import annotations

from typing import Any

import pytest

from better_telegram_mcp.config import Settings


def test_sse_defaults_are_present() -> None:
    settings = Settings()

    assert settings.auth_url == "https://better-telegram-mcp.n24q02m.com"
    assert settings.sse_subscriber_queue_size == 100
    assert settings.sse_heartbeat_seconds == 15
    assert settings.bot_poll_timeout_seconds == 30
    assert settings.bot_poll_backoff_initial_ms == 1000
    assert settings.bot_poll_backoff_max_ms == 60000


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("sse_subscriber_queue_size", 0),
        ("sse_heartbeat_seconds", 0),
        ("bot_poll_timeout_seconds", 0),
        ("bot_poll_backoff_initial_ms", 0),
        ("bot_poll_backoff_max_ms", 0),
    ],
)
def test_sse_defaults_reject_non_positive_values(field_name: str, value: int) -> None:
    kwargs: dict[str, Any] = {field_name: value}

    with pytest.raises(ValueError):
        Settings(**kwargs)


def test_legacy_relay_endpoint_env_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_RELAY_ENDPOINT_URL", "https://example.com/events")

    settings = Settings()

    assert settings.auth_url == "https://better-telegram-mcp.n24q02m.com"
    assert settings.is_configured is False
