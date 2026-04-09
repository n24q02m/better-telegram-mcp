from __future__ import annotations

import pytest

from better_telegram_mcp.config import Settings


def test_sse_defaults_are_present() -> None:
    settings = Settings()

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
    with pytest.raises(ValueError):
        Settings(**{field_name: value})


def test_existing_relay_defaults_stay_unchanged() -> None:
    settings = Settings()

    assert settings.relay_endpoint_url is None
    assert settings.relay_queue_size == 10000
    assert settings.relay_timeout_seconds == 10
    assert settings.relay_max_retries == 5
    assert settings.relay_backoff_initial_ms == 500
    assert settings.relay_backoff_max_ms == 30000
