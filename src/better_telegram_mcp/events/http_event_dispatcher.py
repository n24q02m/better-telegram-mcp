from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import httpx
from loguru import logger

from better_telegram_mcp.config import Settings


class HTTPEventDispatcher:
    def __init__(
        self, settings: Settings, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            timeout=settings.relay_timeout_seconds
        )
        self._owns_client = client is None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=settings.relay_queue_size
        )
        self._worker: asyncio.Task[None] | None = None
        self._accepting_events = False
        self.delivered_count = 0
        self.failed_count = 0
        self.dropped_count = 0

    async def start(self) -> None:
        if self._worker is not None:
            return
        self._accepting_events = True
        self._worker = asyncio.create_task(self._run(), name="http-event-dispatcher")

    def enqueue(self, event: dict[str, Any]) -> bool:
        if not self._accepting_events:
            self.dropped_count += 1
            return False

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped_count += 1
            logger.warning("Shared event relay queue full; dropping event")
            return False
        return True

    async def join(self) -> None:
        await self._queue.join()

    async def stop(self) -> None:
        self._accepting_events = False
        await self.join()

        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None

        if self._owns_client:
            await self._client.aclose()
        else:
            await self._client.aclose()

    async def _run(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._deliver_with_retries(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.failed_count += 1
                logger.warning("Shared event relay delivery failed: {}", exc)
            finally:
                self._queue.task_done()

    async def _deliver_with_retries(self, event: dict[str, Any]) -> None:
        attempt = 0
        while True:
            try:
                response = await self._post_event(event)
            except TypeError:
                self.failed_count += 1
                return
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.ConnectError,
            ) as exc:
                if attempt >= self._settings.relay_max_retries:
                    self.failed_count += 1
                    logger.warning("Shared event relay exhausted retries: {}", exc)
                    return
                await asyncio.sleep(self._backoff_seconds(attempt))
                attempt += 1
                continue

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt >= self._settings.relay_max_retries:
                    self.failed_count += 1
                    logger.warning(
                        "Shared event relay exhausted retries with status {}",
                        response.status_code,
                    )
                    return
                await asyncio.sleep(self._backoff_seconds(attempt))
                attempt += 1
                continue

            if 400 <= response.status_code < 500:
                self.failed_count += 1
                return

            self.delivered_count += 1
            return

    async def _post_event(self, event: Mapping[str, Any]) -> httpx.Response:
        payload = json.loads(json.dumps(event))
        relay_endpoint_url = self._settings.relay_endpoint_url
        if relay_endpoint_url is None:
            msg = "Relay endpoint URL is not configured"
            raise RuntimeError(msg)
        return await self._client.post(relay_endpoint_url, json=payload)

    def _backoff_seconds(self, attempt: int) -> float:
        initial_ms = self._settings.relay_backoff_initial_ms
        max_ms = self._settings.relay_backoff_max_ms
        delay_ms = min(initial_ms * (2**attempt), max_ms)
        return delay_ms / 1000
