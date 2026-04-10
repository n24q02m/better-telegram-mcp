from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

SSECloseReason = Literal["connection_replaced", "overflow", "runtime_stopped"]

T = TypeVar("T")


@dataclass(slots=True)
class SSEFanoutItem:
    kind: Literal["event", "error"]
    event: dict[str, Any] | None = None
    reason: SSECloseReason | None = None


class SSESubscriber:
    def __init__(self, queue: asyncio.Queue[SSEFanoutItem], token: object) -> None:
        self._queue = queue
        self._token = token

    async def next_item(self) -> SSEFanoutItem:
        return await self._queue.get()

    @property
    def token(self) -> object:
        return self._token


@dataclass(slots=True)
class _SubscriberState:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[SSEFanoutItem]
    token: object


class SSESubscriberHub:
    def __init__(self, subscriber_queue_size: int) -> None:
        self._queue_size = subscriber_queue_size
        self._subscriber: _SubscriberState | None = None
        self._closed = False

    def subscribe(self) -> SSESubscriber:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[SSEFanoutItem] = asyncio.Queue(maxsize=self._queue_size)
        token = object()
        state = _SubscriberState(loop=loop, queue=queue, token=token)
        previous = self._subscriber
        self._subscriber = state
        if previous is not None:
            self._dispatch_error(previous, "connection_replaced")
        return SSESubscriber(queue, token)

    def unsubscribe(self, subscriber: SSESubscriber) -> bool:
        current = self._subscriber
        if current is None or current.token is not subscriber.token:
            return False

        if self._in_subscriber_loop(current.loop):
            return self._unsubscribe_in_loop(subscriber.token)
        return self._call_in_loop(
            current.loop,
            lambda: self._unsubscribe_in_loop(subscriber.token),
        )

    def publish(self, event: dict[str, Any]) -> bool:
        if self._closed or self._subscriber is None:
            return False

        subscriber = self._subscriber
        if self._in_subscriber_loop(subscriber.loop):
            return self._publish_to_subscriber(subscriber, event)
        return self._call_in_loop(
            subscriber.loop,
            lambda: self._publish_to_subscriber(subscriber, event),
        )

    async def close(self, reason: SSECloseReason) -> None:
        self._closed = True
        subscriber = self._subscriber
        self._subscriber = None
        if subscriber is not None:
            self._dispatch_error(subscriber, reason)

    def _publish_to_subscriber(
        self, subscriber: _SubscriberState, event: dict[str, Any]
    ) -> bool:
        if self._closed or self._subscriber is not subscriber:
            return False

        try:
            subscriber.queue.put_nowait(SSEFanoutItem(kind="event", event=event))
        except asyncio.QueueFull:
            self._subscriber = None
            self._push_error(subscriber.queue, "overflow")
            return False
        return True

    def _dispatch_error(
        self, subscriber: _SubscriberState, reason: SSECloseReason
    ) -> None:
        if self._in_subscriber_loop(subscriber.loop):
            self._push_error(subscriber.queue, reason)
            return
        self._call_in_loop(
            subscriber.loop, lambda: self._push_error(subscriber.queue, reason)
        )

    def _unsubscribe_in_loop(self, token: object) -> bool:
        current = self._subscriber
        if current is None or current.token is not token:
            return False
        self._subscriber = None
        return True

    def _push_error(
        self, subscriber: asyncio.Queue[SSEFanoutItem], reason: SSECloseReason
    ) -> None:
        for _ in range(self._queue_size + 1):
            try:
                subscriber.put_nowait(SSEFanoutItem(kind="error", reason=reason))
                return
            except asyncio.QueueFull:
                try:
                    subscriber.get_nowait()
                except asyncio.QueueEmpty:
                    return

    @staticmethod
    def _in_subscriber_loop(loop: asyncio.AbstractEventLoop) -> bool:
        try:
            return asyncio.get_running_loop() is loop
        except RuntimeError:
            return False

    @staticmethod
    def _call_in_loop(loop: asyncio.AbstractEventLoop, func: Callable[[], T]) -> T:
        """Schedule func in the subscriber's event loop and block until complete.

        Called only from a different thread/loop (the producer side).
        Same-loop callers take the fast path in publish()/unsubscribe()
        and never reach here. Raises TimeoutError if the subscriber loop
        does not execute the callback within 5 seconds.
        """
        assert not SSESubscriberHub._in_subscriber_loop(loop), (
            "_call_in_loop must not be called from the subscriber's event loop"
        )
        result: Future[T] = Future()

        def runner() -> None:
            try:
                result.set_result(func())
            except Exception as exc:  # pragma: no cover - defensive bridge
                result.set_exception(exc)

        loop.call_soon_threadsafe(runner)
        return result.result(timeout=5.0)
