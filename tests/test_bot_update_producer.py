from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path
from typing import Any, cast

import pytest

from better_telegram_mcp.auth.per_user_session_store import (
    PerUserSessionStore,
    SessionInfo,
)
from better_telegram_mcp.backends.bot_backend import TelegramAPIError
from better_telegram_mcp.backends.bot_update_producer import BotUpdateProducer


@pytest.fixture
def session_store(tmp_path: Path) -> PerUserSessionStore:
    return PerUserSessionStore(tmp_path / "data", secret="test-secret")


class FakeEventSink:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, envelope: dict[str, Any]) -> bool:
        self.events.append(envelope)
        return True


class FakeBotBackend:
    def __init__(
        self,
        *,
        bot_id: int = 200,
        username: str | None = "testbot",
        webhook_info: dict[str, Any] | None = None,
        update_results: list[list[dict[str, Any]] | Exception] | None = None,
    ) -> None:
        bot_info: dict[str, Any] = {"id": bot_id}
        self._bot_info = bot_info
        if username is not None:
            self._bot_info["username"] = username
        self._webhook_info = webhook_info or {"url": ""}
        self._update_results = deque(update_results or [])
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def _call(self, method: str, **params: Any) -> Any:
        self.calls.append((method, params))
        if method == "getWebhookInfo":
            return self._webhook_info
        msg = f"Unexpected method: {method}"
        raise AssertionError(msg)

    async def get_updates(
        self,
        offset: int | None = None,
        timeout: int = 30,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            (
                "get_updates",
                {
                    "offset": offset,
                    "timeout": timeout,
                    "allowed_updates": allowed_updates,
                },
            )
        )
        if not self._update_results:
            return []

        result = self._update_results.popleft()
        if isinstance(result, Exception):
            raise result
        return result


def _make_update(update_id: int, text: str = "hello") -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "text": text,
            "chat": {"id": 1, "type": "private"},
        },
    }


async def test_initialize_skips_existing_backlog_and_persists_offset(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-1"
    session_store.store(
        bearer,
        SessionInfo(session_name="bot-session", mode="bot", bot_token="123:ABC"),
    )
    backend = FakeBotBackend(update_results=[[_make_update(5), _make_update(6)]])
    sink = FakeEventSink()
    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=sink,
    )

    await producer.initialize()

    assert sink.events == []
    assert producer.next_offset == 7
    loaded = session_store.load(bearer)
    assert loaded is not None
    assert loaded.bot_offset == 6
    assert backend.calls == [
        ("getWebhookInfo", {}),
        (
            "get_updates",
            {"offset": None, "timeout": 0, "allowed_updates": None},
        ),
    ]


async def test_poll_once_resumes_from_stored_offset_and_publishes_normalized_event(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-2"
    session_store.store(
        bearer,
        SessionInfo(
            session_name="bot-session",
            mode="bot",
            bot_token="123:ABC",
            bot_offset=10,
        ),
    )
    backend = FakeBotBackend(update_results=[[_make_update(11, text="live")]])
    sink = FakeEventSink()
    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=sink,
    )

    published = await producer.poll_once()

    assert published == 1
    assert producer.next_offset == 12
    loaded = session_store.load(bearer)
    assert loaded is not None
    assert loaded.bot_offset == 11
    assert sink.events[0]["mode"] == "bot"
    assert sink.events[0]["account"] == {
        "telegram_id": 200,
        "session_name": "bot-session",
        "username": "testbot",
        "mode": "bot",
    }
    assert sink.events[0]["update"]["update_id"] == 11
    assert backend.calls == [
        ("getWebhookInfo", {}),
        (
            "get_updates",
            {"offset": 11, "timeout": 30, "allowed_updates": None},
        ),
    ]


async def test_poll_once_skips_duplicate_update_ids(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-3"
    session_store.store(
        bearer,
        SessionInfo(session_name="bot-session", mode="bot", bot_token="123:ABC"),
    )
    backend = FakeBotBackend(
        update_results=[
            [],
            [_make_update(11), _make_update(11), _make_update(12, text="next")],
        ]
    )
    sink = FakeEventSink()
    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=sink,
    )

    await producer.initialize()
    published = await producer.poll_once()

    assert published == 2
    assert [event["update"]["update_id"] for event in sink.events] == [11, 12]
    loaded = session_store.load(bearer)
    assert loaded is not None
    assert loaded.bot_offset == 12


async def test_initialize_rejects_active_webhook(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-4"
    session_store.store(
        bearer,
        SessionInfo(session_name="bot-session", mode="bot", bot_token="123:ABC"),
    )
    backend = FakeBotBackend(webhook_info={"url": "https://example.com/webhook"})
    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=FakeEventSink(),
    )

    with pytest.raises(ValueError, match="webhook"):
        await producer.initialize()


async def test_start_retries_after_transient_failure_with_backoff(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-5"
    session_store.store(
        bearer,
        SessionInfo(
            session_name="bot-session",
            mode="bot",
            bot_token="123:ABC",
            bot_offset=20,
        ),
    )
    backend = FakeBotBackend(
        update_results=[
            TelegramAPIError("Too Many Requests", 429),
            [_make_update(21, text="recovered")],
        ]
    )
    sink = FakeEventSink()
    sleep_calls: list[float] = []
    recovered = asyncio.Event()

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)
        await asyncio.sleep(0)

    original_publish = sink.publish

    def publish_and_signal(envelope: dict[str, Any]) -> bool:
        result = original_publish(envelope)
        recovered.set()
        return result

    sink.publish = publish_and_signal

    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=sink,
        backoff_initial_ms=50,
        backoff_max_ms=200,
        sleep=fake_sleep,
    )

    await producer.start()
    await asyncio.wait_for(recovered.wait(), timeout=1)
    await producer.stop()

    assert sleep_calls == [0.05]
    assert [event["update"]["update_id"] for event in sink.events] == [21]
    loaded = session_store.load(bearer)
    assert loaded is not None
    assert loaded.bot_offset == 21


async def test_start_stops_on_auth_failure_without_retry(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-6"
    session_store.store(
        bearer,
        SessionInfo(
            session_name="bot-session",
            mode="bot",
            bot_token="123:ABC",
            bot_offset=30,
        ),
    )
    backend = FakeBotBackend(update_results=[TelegramAPIError("Unauthorized", 401)])
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=FakeEventSink(),
        sleep=fake_sleep,
    )

    await producer.start()
    task = producer._task
    assert task is not None
    await asyncio.wait_for(asyncio.shield(task), timeout=1)

    assert sleep_calls == []
    assert isinstance(producer.last_error, TelegramAPIError)
    assert str(producer.last_error) == "Unauthorized"
    loaded = session_store.load(bearer)
    assert loaded is not None
    assert loaded.bot_offset == 30


async def test_start_stops_after_max_retries(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-6b"
    session_store.store(
        bearer,
        SessionInfo(
            session_name="bot-session",
            mode="bot",
            bot_token="123:ABC",
            bot_offset=30,
        ),
    )
    backend = FakeBotBackend(
        update_results=cast(
            list[list[dict[str, Any]] | Exception],
            [TelegramAPIError("Too Many Requests", 429)] * 3,
        )
    )
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=FakeEventSink(),
        backoff_initial_ms=50,
        backoff_max_ms=200,
        max_retries=3,
        sleep=fake_sleep,
    )

    await producer.start()
    task = producer._task
    assert task is not None
    await asyncio.wait_for(asyncio.shield(task), timeout=1)

    assert sleep_calls == [0.05, 0.1]
    assert isinstance(producer.last_error, TelegramAPIError)
    assert str(producer.last_error) == "Too Many Requests"
    assert producer.is_running is False


async def test_stop_waits_for_in_flight_batch_to_persist_offset(
    session_store: PerUserSessionStore,
) -> None:
    bearer = "bearer-7"
    session_store.store(
        bearer,
        SessionInfo(
            session_name="bot-session",
            mode="bot",
            bot_token="123:ABC",
            bot_offset=50,
        ),
    )

    poll_started = asyncio.Event()
    release_poll = asyncio.Event()

    class BlockingBotBackend(FakeBotBackend):
        async def get_updates(
            self,
            offset: int | None = None,
            timeout: int = 30,
            allowed_updates: list[str] | None = None,
        ) -> list[dict[str, Any]]:
            self.calls.append(
                (
                    "get_updates",
                    {
                        "offset": offset,
                        "timeout": timeout,
                        "allowed_updates": allowed_updates,
                    },
                )
            )
            poll_started.set()
            await release_poll.wait()
            return [_make_update(51, text="persist me")]

    backend = BlockingBotBackend()
    sink = FakeEventSink()
    producer = BotUpdateProducer(
        backend=backend,
        session_store=session_store,
        bearer=bearer,
        event_sink=sink,
    )

    await producer.start()
    await asyncio.wait_for(poll_started.wait(), timeout=1)

    stop_task = asyncio.create_task(producer.stop())
    await asyncio.sleep(0)
    release_poll.set()
    await asyncio.wait_for(stop_task, timeout=1)

    assert [event["update"]["update_id"] for event in sink.events] == [51]
    loaded = session_store.load(bearer)
    assert loaded is not None
    assert loaded.bot_offset == 51
    assert producer.is_running is False
