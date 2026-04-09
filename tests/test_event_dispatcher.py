from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx

from better_telegram_mcp.config import Settings
from better_telegram_mcp.events import HTTPEventDispatcher, build_event_envelope


def _make_settings(**overrides: object) -> Settings:
    return Settings(
        relay_endpoint_url="https://example.com/events",
        relay_queue_size=10,
        relay_timeout_seconds=1,
        relay_max_retries=3,
        relay_backoff_initial_ms=10,
        relay_backoff_max_ms=50,
        **overrides,
    )


def _make_update() -> dict[str, object]:
    return {
        "_": "UpdateNewMessage",
        "message": {"id": 1, "message": "hello"},
    }


def _make_account(**overrides: object) -> dict[str, object]:
    return {
        "telegram_user_id": 100,
        "session_name": "alice",
        "username": "alice_user",
        **overrides,
    }


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://example.com/events"),
    )


def test_build_event_envelope_is_deterministic() -> None:
    account = _make_account()
    update = _make_update()

    first = build_event_envelope(account, update)
    second = build_event_envelope(account, update)

    assert first["event_id"] == second["event_id"]
    assert first["event_type"] == "UpdateNewMessage"
    assert first["account"]["telegram_user_id"] == 100
    assert first["account"]["session_name"] == "alice"
    assert first["update"] == update


def test_build_event_envelope_changes_event_id_for_different_account() -> None:
    update = _make_update()

    first = build_event_envelope(_make_account(telegram_user_id=100), update)
    second = build_event_envelope(_make_account(telegram_user_id=200), update)

    assert first["event_id"] != second["event_id"]


def test_build_event_envelope_excludes_sensitive_fields() -> None:
    envelope = build_event_envelope(
        _make_account(phone="+1234567890", bearer_token="secret"),
        _make_update(),
    )

    assert "phone" not in envelope["account"]
    assert "bearer_token" not in envelope["account"]


async def test_dispatcher_posts_event_successfully() -> None:
    client = AsyncMock()
    client.post = AsyncMock(return_value=_response(202))
    client.aclose = AsyncMock()
    dispatcher = HTTPEventDispatcher(_make_settings(), client=client)

    await dispatcher.start()
    assert (
        dispatcher.enqueue(build_event_envelope(_make_account(), _make_update()))
        is True
    )
    await asyncio.wait_for(dispatcher.join(), timeout=1)
    await dispatcher.stop()

    client.post.assert_awaited_once()
    client.aclose.assert_awaited_once()
    assert dispatcher.delivered_count == 1
    assert dispatcher.failed_count == 0


async def test_dispatcher_retries_transient_failure(monkeypatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    client = AsyncMock()
    client.post = AsyncMock(side_effect=[httpx.ConnectTimeout("boom"), _response(202)])
    client.aclose = AsyncMock()
    dispatcher = HTTPEventDispatcher(_make_settings(), client=client)

    monkeypatch.setattr(
        "better_telegram_mcp.events.http_event_dispatcher.asyncio.sleep", fake_sleep
    )

    await dispatcher.start()
    assert (
        dispatcher.enqueue(build_event_envelope(_make_account(), _make_update()))
        is True
    )
    await asyncio.wait_for(dispatcher.join(), timeout=1)
    await dispatcher.stop()

    assert client.post.await_count == 2
    assert sleeps == [0.01]
    assert dispatcher.delivered_count == 1


async def test_dispatcher_does_not_retry_permanent_failure() -> None:
    client = AsyncMock()
    client.post = AsyncMock(return_value=_response(400))
    client.aclose = AsyncMock()
    dispatcher = HTTPEventDispatcher(_make_settings(), client=client)

    await dispatcher.start()
    assert (
        dispatcher.enqueue(build_event_envelope(_make_account(), _make_update()))
        is True
    )
    await asyncio.wait_for(dispatcher.join(), timeout=1)
    await dispatcher.stop()

    client.post.assert_awaited_once()
    assert dispatcher.failed_count == 1


async def test_dispatcher_queue_full_drops_when_queue_is_full() -> None:
    client = AsyncMock()
    client.post = AsyncMock(return_value=_response(202))
    client.aclose = AsyncMock()
    dispatcher = HTTPEventDispatcher(_make_settings(), client=client)

    dispatcher._queue.put_nowait(build_event_envelope(_make_account(), _make_update()))

    assert (
        dispatcher.enqueue(build_event_envelope(_make_account(), _make_update()))
        is False
    )
    assert dispatcher.dropped_count == 1


async def test_dispatcher_handles_serialization_failure_without_retry() -> None:
    client = AsyncMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    dispatcher = HTTPEventDispatcher(_make_settings(), client=client)

    await dispatcher.start()
    assert dispatcher.enqueue({"bad": {1, 2, 3}}) is True
    await asyncio.wait_for(dispatcher.join(), timeout=1)
    await dispatcher.stop()

    client.post.assert_not_awaited()
    assert dispatcher.failed_count == 1
