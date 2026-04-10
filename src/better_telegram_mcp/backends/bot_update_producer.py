from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from loguru import logger

from ..auth.per_user_session_store import PerUserSessionStore
from ..events.types import EventSink, build_event_envelope
from .bot_backend import TelegramAPIError

if TYPE_CHECKING:
    from .bot_backend import BotBackend


class BotUpdateProducer:
    """Long-poll Bot API updates and publish normalized envelopes."""

    def __init__(
        self,
        *,
        backend: BotBackend,
        session_store: PerUserSessionStore,
        bearer: str,
        event_sink: EventSink,
        poll_timeout_seconds: int = 30,
        backoff_initial_ms: int = 1000,
        backoff_max_ms: int = 60000,
        max_retries: int = 10,
        allowed_updates: list[str] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        offset_persist_interval_seconds: float = 5.0,
    ) -> None:
        self._backend = backend
        self._session_store = session_store
        self._bearer = bearer
        self._event_sink = event_sink
        self._poll_timeout_seconds = poll_timeout_seconds
        self._backoff_initial_ms = backoff_initial_ms
        self._backoff_max_ms = backoff_max_ms
        self._max_retries = max_retries
        self._allowed_updates = allowed_updates
        self._sleep = sleep

        self._offset_persist_interval = offset_persist_interval_seconds
        self._dirty_offset: int | None = None
        self._last_persist_time: float = float("-inf")

        self._account: dict[str, object] | None = None
        self._next_offset: int | None = None
        self._last_persisted_offset: int | None = None
        self._initialized = False
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._last_error: Exception | None = None

    @property
    def next_offset(self) -> int | None:
        return self._next_offset

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def initialize(self) -> None:
        if self._initialized:
            return

        session_info = self._load_session_info()
        webhook_info = await self._backend.call_api("getWebhookInfo")
        if isinstance(webhook_info, dict) and webhook_info.get("url"):
            msg = "Bot long polling cannot start while a webhook is configured"
            raise ValueError(msg)

        self._account = self._build_account(session_info.session_name)
        self._last_persisted_offset = session_info.bot_offset

        if session_info.bot_offset is not None:
            self._next_offset = session_info.bot_offset + 1
        else:
            await self._drain_backlog_to_live_boundary()

        self._initialized = True

    async def poll_once(self) -> int:
        await self.initialize()

        updates = await self._backend.get_updates(
            offset=self._next_offset,
            timeout=self._poll_timeout_seconds,
            allowed_updates=self._allowed_updates,
        )

        published = 0
        highest_seen = self._last_persisted_offset
        seen_update_ids: set[int] = set()
        account = self._require_account()

        for update in updates:
            update_id = self._update_id(update)
            if highest_seen is not None and update_id <= highest_seen:
                continue
            if update_id in seen_update_ids:
                continue

            seen_update_ids.add(update_id)
            if not self._event_sink.publish(build_event_envelope(account, update)):
                logger.debug("Event sink dropped update_id={}", update_id)
                highest_seen = update_id
                continue
            published += 1
            highest_seen = update_id

        if highest_seen is not None and highest_seen != self._last_persisted_offset:
            await self._persist_offset(highest_seen)
            self._last_persisted_offset = highest_seen
            self._next_offset = highest_seen + 1

        return published

    async def start(self) -> None:
        await self.initialize()
        if self.is_running:
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            await self._flush_offset()
            return
        if not self._task.done():
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._task),
                    timeout=max(self._poll_timeout_seconds + 1, 1),
                )
            except TimeoutError:
                self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        await self._flush_offset()
        self._task = None

    async def _run(self) -> None:
        backoff_ms = self._backoff_initial_ms
        retry_count = 0

        while not self._stop_event.is_set():
            try:
                await self.poll_once()
                backoff_ms = self._backoff_initial_ms
                retry_count = 0
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                raise
            except TelegramAPIError as exc:
                if self._is_auth_error(exc):
                    self._last_error = exc
                    self._stop_event.set()
                    return
                retry_count += 1
                if retry_count >= self._max_retries:
                    self._last_error = exc
                    self._stop_event.set()
                    return
                await self._sleep(backoff_ms / 1000)
                backoff_ms = min(backoff_ms * 2, self._backoff_max_ms)
            except Exception as exc:
                self._last_error = exc
                retry_count += 1
                if retry_count >= self._max_retries:
                    self._stop_event.set()
                    return
                await self._sleep(backoff_ms / 1000)
                backoff_ms = min(backoff_ms * 2, self._backoff_max_ms)

    def _load_session_info(self) -> Any:
        session_info = self._session_store.load(self._bearer)
        if session_info is None:
            msg = "No persisted bot session for bearer"
            raise ValueError(msg)
        return session_info

    def _build_account(self, session_name: str) -> dict[str, object]:
        bot_info = self._backend.bot_info
        account: dict[str, object] = {
            "telegram_id": int(bot_info["id"]),
            "session_name": session_name,
            "mode": "bot",
        }
        username = bot_info.get("username")
        if username:
            account["username"] = username
        return account

    def _require_account(self) -> dict[str, object]:
        if self._account is None:
            msg = "Bot producer account metadata is not initialized"
            raise RuntimeError(msg)
        return self._account

    async def _drain_backlog_to_live_boundary(self) -> None:
        backlog = await self._backend.get_updates(
            offset=None,
            timeout=0,
            allowed_updates=self._allowed_updates,
        )
        if not backlog:
            return

        last_update_id = max(self._update_id(update) for update in backlog)
        await self._persist_offset(last_update_id)
        await self._flush_offset()
        self._last_persisted_offset = last_update_id
        self._next_offset = last_update_id + 1

    async def _persist_offset(self, bot_offset: int) -> None:
        self._dirty_offset = bot_offset
        now = time.monotonic()
        if now - self._last_persist_time >= self._offset_persist_interval:
            await self._flush_offset()

    async def _flush_offset(self) -> None:
        if self._dirty_offset is None:
            return
        offset = self._dirty_offset
        bearer = self._bearer

        def _write() -> None:
            session_info = self._session_store.load(bearer)
            if session_info is None:
                return
            session_info.bot_offset = offset
            self._session_store.store(bearer, session_info)

        await asyncio.to_thread(_write)
        self._last_persist_time = time.monotonic()
        self._dirty_offset = None

    @staticmethod
    def _update_id(update: dict[str, Any]) -> int:
        return int(update["update_id"])

    @staticmethod
    def _is_auth_error(exc: TelegramAPIError) -> bool:
        if exc.error_code in {401, 403}:
            return True
        return "unauthorized" in str(exc).lower()
