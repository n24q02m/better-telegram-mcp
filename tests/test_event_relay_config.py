from __future__ import annotations

import pytest

from better_telegram_mcp.backends.security import SecurityError
from better_telegram_mcp.config import Settings


def test_relay_endpoint_accepts_valid_https_url() -> None:
    settings = Settings(relay_endpoint_url="https://example.com/events")

    assert settings.relay_endpoint_url == "https://example.com/events"
    assert settings.mode == "bot"


def test_invalid_relay_endpoint_rejects_private_url() -> None:
    with pytest.raises(SecurityError, match="blocked"):
        Settings(relay_endpoint_url="http://127.0.0.1/events")


def test_relay_endpoint_empty_string_disables_relay() -> None:
    settings = Settings(relay_endpoint_url="   ")

    assert settings.relay_endpoint_url is None


def test_relay_defaults_are_present() -> None:
    settings = Settings()

    assert settings.relay_endpoint_url is None
    assert settings.relay_queue_size == 10000
    assert settings.relay_timeout_seconds == 10
    assert settings.relay_max_retries == 5
    assert settings.relay_backoff_initial_ms == 500
    assert settings.relay_backoff_max_ms == 30000
