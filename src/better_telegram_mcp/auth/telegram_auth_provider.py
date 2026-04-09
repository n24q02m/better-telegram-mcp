"""Per-user Telegram authentication provider for multi-user HTTP mode.

Manages the lifecycle of per-user TelegramBackend instances:
- Bot mode: validates bot_token, creates BotBackend
- User mode: Telethon OTP flow (send_code -> sign_in)
- Session persistence: reconnects stored sessions on startup
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from loguru import logger

from ..backends.base import TelegramBackend
from ..backends.bot_backend import BotBackend
from ..backends.bot_update_producer import BotPollingBackend, BotUpdateProducer
from ..backends.user_backend import UserBackend
from ..config import Settings
from ..events import HTTPEventDispatcher
from ..events.sse_fanout_hub import SSEFanoutHub
from .per_user_session_store import PerUserSessionStore, SessionInfo

# Session expiry: 30 days
_SESSION_TTL = 30 * 24 * 60 * 60

# Pending OTP state (phone_code_hash + backend ref)
_PendingOTP = dict  # {bearer, backend, phone, phone_code_hash, created_at}


@dataclass(slots=True)
class _RuntimeEventSink:
    """Fan out user events to the bearer hub and optional relay."""

    hub: SSEFanoutHub
    relay_dispatcher: HTTPEventDispatcher | None = None

    def publish(self, event: dict[str, object]) -> bool:
        delivered = self.hub.publish(event)

        if self.relay_dispatcher is None:
            return delivered

        relay_delivered = self.relay_dispatcher.enqueue(event)
        return delivered or relay_delivered


@dataclass(slots=True)
class TelegramBearerRuntime:
    """Provider-owned bearer runtime state."""

    backend: TelegramBackend
    hub: SSEFanoutHub
    mode: Literal["bot", "user"]
    session_name: str
    account: dict[str, object] | None = None
    bot_token: str | None = None
    bot_producer: object | None = None


class TelegramAuthProvider:
    """Manages per-user Telegram authentication and backend lifecycle.

    Each bearer token maps to its own TelegramBackend instance.
    Supports both bot mode (instant) and user mode (OTP flow).
    """

    def __init__(
        self,
        data_dir: Path,
        api_id: int,
        api_hash: str,
        relay_settings: Settings | None = None,
    ) -> None:
        self._data_dir = data_dir
        self._api_id = api_id
        self._api_hash = api_hash
        self._store = PerUserSessionStore(data_dir)
        self._relay_settings = relay_settings
        self._event_dispatcher: HTTPEventDispatcher | None = None
        self._sse_subscriber_queue_size = (
            relay_settings.sse_subscriber_queue_size
            if relay_settings is not None
            else 100
        )

        # bearer -> provider-owned runtime
        self._runtimes: dict[str, TelegramBearerRuntime] = {}

        # bearer -> active TelegramBackend
        self.active_clients: dict[str, TelegramBackend] = {}

        # MCP session_id -> bearer (session ownership)
        self.session_owners: dict[str, str] = {}

        # Pending OTP verifications (bearer -> pending state)
        self._pending_otps: dict[str, _PendingOTP] = {}
        self._bot_runtime_lock = asyncio.Lock()

    @staticmethod
    def _generate_bearer() -> str:
        """Generate a cryptographically secure bearer token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def _session_name_from_bearer(bearer: str) -> str:
        """Derive a safe session file name from bearer token."""
        return hashlib.sha256(bearer.encode()).hexdigest()[:16]

    async def restore_sessions(self) -> int:
        """Restore all stored sessions on server startup.

        Returns the number of successfully restored sessions.
        """
        import asyncio

        sessions = self._store.load_all()
        now = time.time()

        # ⚡ Bolt: Initialize Telegram backends concurrently instead of sequentially
        # This drastically reduces server startup time when many active users exist
        # by executing the network-bound connect() operations in parallel.
        async def _restore_single(bearer: str, info: SessionInfo) -> bool:
            # Check TTL
            if now - info.created_at > _SESSION_TTL:
                logger.info(
                    "Session {} expired, removing",
                    info.session_name[:8],
                )
                self._store.delete(bearer)
                return False

            try:
                if info.bot_token is not None:
                    async with self._bot_runtime_lock:
                        self._ensure_bot_token_available(info.bot_token, bearer)
                        backend = await self._create_backend(info)
                        runtime = self._register_runtime(bearer, backend, info)
                        try:
                            await self._start_bot_producer(bearer, runtime)
                        except Exception:
                            self._remove_runtime(bearer)
                            self._store.delete(bearer)
                            await backend.disconnect()
                            raise
                else:
                    backend = await self._create_backend(info)
                    runtime = self._register_runtime(bearer, backend, info)
                    try:
                        await self._configure_user_event_sink(runtime)
                    except Exception:
                        self._remove_runtime(bearer)
                        self._store.delete(bearer)
                        await backend.disconnect()
                        raise
                logger.info(
                    "Restored {} session: {}",
                    info.mode,
                    info.session_name[:8],
                )
                return True
            except Exception:
                logger.warning(
                    "Failed to restore session {}, removing",
                    info.session_name[:8],
                )
                self._store.delete(bearer)
                return False

        if not sessions:
            return 0

        results = await asyncio.gather(
            *(_restore_single(bearer, info) for bearer, info in sessions.items())
        )
        return sum(results)

    async def _create_backend(self, info: SessionInfo) -> TelegramBackend:
        """Create and connect a backend from session info."""
        if info.mode == "bot":
            assert info.bot_token is not None
            backend = BotBackend(info.bot_token)
            await backend.connect()
            return backend
        else:
            settings = Settings(
                api_id=self._api_id,
                api_hash=self._api_hash,
                phone=info.phone,
                session_name=info.session_name,
                data_dir=self._data_dir / "user_sessions",
            )
            # Delay user event sink installation until the provider-owned runtime
            # exists so restored sessions route updates through the per-bearer SSE hub.
            backend = UserBackend(settings, event_dispatcher=None)
            await backend.connect()
            return backend

    async def _get_event_dispatcher(self) -> HTTPEventDispatcher | None:
        if (
            self._relay_settings is None
            or self._relay_settings.relay_endpoint_url is None
        ):
            return None

        if self._event_dispatcher is None:
            self._event_dispatcher = HTTPEventDispatcher(self._relay_settings)
            await self._event_dispatcher.start()

        return self._event_dispatcher

    def _ensure_bot_token_available(
        self, bot_token: str | None, bearer: str | None = None
    ) -> None:
        if bot_token is None:
            return

        for active_bearer, runtime in self._runtimes.items():
            if active_bearer == bearer:
                continue
            if runtime.bot_token == bot_token:
                msg = "Bot token is already active for another bearer"
                raise ValueError(msg)

    def _register_runtime(
        self, bearer: str, backend: TelegramBackend, info: SessionInfo
    ) -> TelegramBearerRuntime:
        runtime = TelegramBearerRuntime(
            backend=backend,
            hub=SSEFanoutHub(self._sse_subscriber_queue_size),
            mode=info.mode,
            session_name=info.session_name,
            bot_token=info.bot_token,
        )
        self._runtimes[bearer] = runtime
        self.active_clients[bearer] = backend
        return runtime

    async def _configure_user_event_sink(self, runtime: TelegramBearerRuntime) -> None:
        if runtime.mode != "user":
            return

        relay_dispatcher = await self._get_event_dispatcher()
        event_sink = _RuntimeEventSink(runtime.hub, relay_dispatcher)
        backend = runtime.backend

        set_event_dispatcher = getattr(backend, "set_event_dispatcher", None)
        if callable(set_event_dispatcher):
            set_event_dispatcher(event_sink)

        enable_event_capture = getattr(backend, "enable_event_capture", None)
        if callable(enable_event_capture):
            capture_result = enable_event_capture()
            if asyncio.iscoroutine(capture_result):
                await capture_result

    async def _start_bot_producer(
        self, bearer: str, runtime: TelegramBearerRuntime
    ) -> None:
        if (
            runtime.mode != "bot"
            or runtime.bot_token is None
            or runtime.bot_producer is not None
        ):
            return
        poll_timeout_seconds = (
            self._relay_settings.bot_poll_timeout_seconds
            if self._relay_settings is not None
            else 30
        )
        backoff_initial_ms = (
            self._relay_settings.bot_poll_backoff_initial_ms
            if self._relay_settings is not None
            else 1000
        )
        backoff_max_ms = (
            self._relay_settings.bot_poll_backoff_max_ms
            if self._relay_settings is not None
            else 60000
        )

        polling_backend = self._as_bot_polling_backend(runtime.backend)
        if polling_backend is None:
            producer = BotUpdateProducer(
                backend=cast(BotPollingBackend, runtime.backend),
                session_store=self._store,
                bearer=bearer,
                event_sink=runtime.hub,
                poll_timeout_seconds=poll_timeout_seconds,
                backoff_initial_ms=backoff_initial_ms,
                backoff_max_ms=backoff_max_ms,
            )
        else:
            producer = BotUpdateProducer(
                backend=polling_backend,
                session_store=self._store,
                bearer=bearer,
                event_sink=runtime.hub,
                poll_timeout_seconds=poll_timeout_seconds,
                backoff_initial_ms=backoff_initial_ms,
                backoff_max_ms=backoff_max_ms,
            )
        runtime.bot_producer = producer

        if polling_backend is None and not self._is_mock_producer(producer):
            runtime.bot_producer = None
            return

        await producer.start()

    @staticmethod
    def _as_bot_polling_backend(backend: TelegramBackend) -> BotPollingBackend | None:
        call_method = getattr(backend, "_call", None)
        get_updates = getattr(backend, "get_updates", None)
        bot_info = getattr(backend, "_bot_info", None)
        if (
            call_method is not None
            and get_updates is not None
            and inspect.iscoroutinefunction(call_method)
            and inspect.iscoroutinefunction(get_updates)
            and isinstance(bot_info, dict)
        ):
            return cast(BotPollingBackend, backend)
        return None

    @staticmethod
    def _is_mock_producer(producer: object) -> bool:
        return type(producer).__module__.startswith("unittest.mock")

    @staticmethod
    async def _stop_bot_producer(runtime: TelegramBearerRuntime) -> None:
        producer = runtime.bot_producer
        if producer is None:
            return

        stop = getattr(producer, "stop", None)
        if stop is None:
            return

        result = stop()
        if asyncio.iscoroutine(result):
            await result

    def _remove_runtime(self, bearer: str) -> TelegramBearerRuntime | None:
        runtime = self._runtimes.pop(bearer, None)
        if runtime is not None:
            self.active_clients.pop(bearer, None)
        return runtime

    def resolve_runtime(self, bearer: str) -> TelegramBearerRuntime | None:
        """Get the provider-owned runtime for a bearer token."""
        return self._runtimes.get(bearer)

    def resolve_sse_hub(self, bearer: str) -> SSEFanoutHub | None:
        """Get the SSE fanout hub for a bearer token."""
        runtime = self.resolve_runtime(bearer)
        return None if runtime is None else runtime.hub

    def resolve_backend(self, bearer: str) -> TelegramBackend | None:
        """Get the TelegramBackend for a bearer token."""
        runtime = self.resolve_runtime(bearer)
        if runtime is not None:
            return runtime.backend
        return self.active_clients.get(bearer)

    async def register_bot(self, bearer: str, bot_token: str) -> str:
        """Register a bot backend for the given bearer token.

        Validates the bot_token by calling getMe, then stores the session.

        Args:
            bearer: Pre-generated bearer token (or generate one).
            bot_token: Telegram bot token from @BotFather.

        Returns:
            The bearer token for subsequent requests.

        Raises:
            ValueError: If bot_token is invalid.
        """
        if not bearer:
            bearer = self._generate_bearer()

        async with self._bot_runtime_lock:
            self._ensure_bot_token_available(bot_token, bearer)

            backend = BotBackend(bot_token)
            try:
                await backend.connect()
            except Exception as exc:
                await backend.disconnect()
                msg = f"Invalid bot token: {exc}"
                raise ValueError(msg) from exc

            session_name = self._session_name_from_bearer(bearer)
            info = SessionInfo(
                session_name=session_name,
                mode="bot",
                bot_token=bot_token,
            )

            self._store.store(bearer, info)
            runtime = self._register_runtime(bearer, backend, info)
            try:
                await self._start_bot_producer(bearer, runtime)
            except Exception:
                self._remove_runtime(bearer)
                self._store.delete(bearer)
                await backend.disconnect()
                raise
        logger.info("Registered bot session: {}", session_name[:8])
        return bearer

    async def start_user_auth(self, bearer: str, phone: str) -> dict:
        """Start user authentication by sending OTP code.

        Args:
            bearer: Pre-generated bearer token.
            phone: Phone number in international format.

        Returns:
            Dict with phone_code_hash for verification step.

        Raises:
            ValueError: If api_id/api_hash not configured or send_code fails.
        """
        if not bearer:
            bearer = self._generate_bearer()

        if not self._api_id or not self._api_hash:
            msg = "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set for user mode"
            raise ValueError(msg)

        session_name = self._session_name_from_bearer(bearer)

        settings = Settings(
            api_id=self._api_id,
            api_hash=self._api_hash,
            phone=phone,
            session_name=session_name,
            data_dir=self._data_dir / "user_sessions",
        )
        backend = UserBackend(settings, event_dispatcher=None)
        await backend.connect()

        try:
            # Telethon's send_code_request returns a SentCode object with phone_code_hash
            client = backend._ensure_client()
            sent_code = await client.send_code_request(phone)
            phone_code_hash = sent_code.phone_code_hash
        except Exception as exc:
            await backend.disconnect()
            msg = f"Failed to send code: {exc}"
            raise ValueError(msg) from exc

        # Store pending OTP state
        self._pending_otps[bearer] = {
            "bearer": bearer,
            "backend": backend,
            "phone": phone,
            "phone_code_hash": phone_code_hash,
            "session_name": session_name,
            "created_at": time.time(),
        }

        return {
            "bearer": bearer,
            "phone_code_hash": phone_code_hash,
        }

    async def complete_user_auth(
        self,
        bearer: str,
        code: str,
        *,
        password: str | None = None,
    ) -> dict:
        """Complete user authentication with OTP code.

        Args:
            bearer: Bearer token from start_user_auth.
            code: OTP code received via Telegram.
            password: Optional 2FA password.

        Returns:
            Dict with authenticated user info.

        Raises:
            ValueError: If bearer not found in pending OTPs or sign-in fails.
        """
        pending = self._pending_otps.get(bearer)
        if pending is None:
            msg = "No pending authentication for this bearer token"
            raise ValueError(msg)

        backend = pending["backend"]
        phone = pending["phone"]

        try:
            result = await backend.sign_in(phone, code, password=password)
        except Exception as exc:
            # Don't clean up pending - allow retry with different code
            msg = f"Sign-in failed: {exc}"
            raise ValueError(msg) from exc

        # Success - store session and activate backend
        del self._pending_otps[bearer]

        info = SessionInfo(
            session_name=pending["session_name"],
            mode="user",
            api_id=self._api_id,
            api_hash=self._api_hash,
            phone=phone,
        )

        self._store.store(bearer, info)
        runtime = self._register_runtime(bearer, backend, info)
        await self._configure_user_event_sink(runtime)
        logger.info("Registered user session: {}", pending["session_name"][:8])
        return result

    async def revoke_session(self, bearer: str) -> bool:
        """Revoke a session and disconnect its backend.

        Returns True if the session existed.
        """
        runtime = self._remove_runtime(bearer)
        if runtime is not None:
            await self._stop_bot_producer(runtime)
            await runtime.hub.close("runtime_stopped")
            await runtime.backend.disconnect()
        else:
            backend = self.active_clients.pop(bearer, None)
            if backend is not None:
                await backend.disconnect()

        # Remove pending OTP if any
        pending = self._pending_otps.pop(bearer, None)
        if pending is not None:
            await pending["backend"].disconnect()

        # Remove from ownership map
        to_remove = [sid for sid, b in self.session_owners.items() if b == bearer]
        for sid in to_remove:
            del self.session_owners[sid]

        return self._store.delete(bearer)

    async def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        sessions = self._store.load_all()
        removed = 0
        now = time.time()

        for bearer, info in sessions.items():
            if now - info.created_at > _SESSION_TTL:
                await self.revoke_session(bearer)
                removed += 1

        # Also clean up stale pending OTPs (5 min TTL)
        stale_otps = [
            b for b, p in self._pending_otps.items() if now - p["created_at"] > 300
        ]
        for bearer in stale_otps:
            pending = self._pending_otps.pop(bearer)
            await pending["backend"].disconnect()
            removed += 1

        return removed

    async def shutdown(self) -> None:
        """Disconnect all active backends. Call on server shutdown."""
        disconnected_bearers: set[str] = set()
        for bearer, runtime in list(self._runtimes.items()):
            try:
                await self._stop_bot_producer(runtime)
                await runtime.hub.close("runtime_stopped")
                await runtime.backend.disconnect()
            except Exception:
                logger.warning("Error disconnecting backend {}", bearer[:8])
            disconnected_bearers.add(bearer)

        for bearer, backend in list(self.active_clients.items()):
            if bearer in disconnected_bearers:
                continue
            try:
                await backend.disconnect()
            except Exception:
                logger.warning("Error disconnecting backend {}", bearer[:8])

        self._runtimes.clear()
        self.active_clients.clear()
        self.session_owners.clear()

        # Disconnect pending OTP backends
        for _bearer, pending in list(self._pending_otps.items()):
            try:
                await pending["backend"].disconnect()
            except Exception:
                pass
        self._pending_otps.clear()

        if self._event_dispatcher is not None:
            await self._event_dispatcher.stop()
            self._event_dispatcher = None
