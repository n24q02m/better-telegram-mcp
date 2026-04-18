"""Per-user Telegram authentication provider for multi-user HTTP mode.

Manages the lifecycle of per-user TelegramBackend instances:
- Bot mode: validates bot_token, creates BotBackend
- User mode: Telethon OTP flow (send_code -> sign_in)
- Session persistence: reconnects stored sessions on startup
"""

from __future__ import annotations

import hashlib
import secrets
import time
from pathlib import Path

from loguru import logger

from ..backends.base import TelegramBackend
from ..backends.bot_backend import BotBackend
from ..backends.user_backend import UserBackend
from ..config import Settings
from .per_user_session_store import PerUserSessionStore, SessionInfo

# Session expiry: 30 days
_SESSION_TTL = 30 * 24 * 60 * 60

# Pending OTP state (phone_code_hash + backend ref)
_PendingOTP = dict  # {bearer, backend, phone, phone_code_hash, created_at}


class TelegramAuthProvider:
    """Manages per-user Telegram authentication and backend lifecycle.

    Each bearer token maps to its own TelegramBackend instance.
    Supports both bot mode (instant) and user mode (OTP flow).
    """

    def __init__(self, data_dir: Path, api_id: int, api_hash: str) -> None:
        self._data_dir = data_dir
        self._api_id = api_id
        self._api_hash = api_hash
        self._store = PerUserSessionStore(data_dir)

        # bearer -> active TelegramBackend
        self.active_clients: dict[str, TelegramBackend] = {}

        # MCP session_id -> bearer (session ownership)
        self.session_owners: dict[str, str] = {}

        # Pending OTP verifications (bearer -> pending state)
        self._pending_otps: dict[str, _PendingOTP] = {}

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
                backend = await self._create_backend(info)
                self.active_clients[bearer] = backend
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
            backend = UserBackend(settings)
            await backend.connect()
            return backend

    def resolve_backend(self, bearer: str) -> TelegramBackend | None:
        """Get the TelegramBackend for a bearer token."""
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
        self.active_clients[bearer] = backend
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
        backend = UserBackend(settings)
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

        # Store pending OTP state.
        # Pop any existing entry first so the new entry is appended at the end,
        # keeping dict insertion order aligned with chronological created_at.
        # This enables O(1) early-exit cleanup in cleanup_expired().
        if (existing := self._pending_otps.pop(bearer, None)) is not None:
            await existing["backend"].disconnect()

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
        self.active_clients[bearer] = backend
        logger.info("Registered user session: {}", pending["session_name"][:8])
        return result

    async def revoke_session(self, bearer: str) -> bool:
        """Revoke a session and disconnect its backend.

        Returns True if the session existed.
        """
        backend = self.active_clients.pop(bearer, None)
        if backend is not None:
            await backend.disconnect()

        # Remove pending OTP if any
        pending = self._pending_otps.pop(bearer, None)
        if pending is not None:
            await pending["backend"].disconnect()

        # Remove from ownership map
        self.session_owners = {
            sid: b for sid, b in self.session_owners.items() if b != bearer
        }

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

        # Clean up stale pending OTPs (5 min TTL) using chronological insertion order.
        # Since start_user_auth pops-then-reinserts each bearer, the oldest entries
        # are always at the front, so we can stop at the first non-stale entry instead
        # of scanning the full dict on every cleanup tick.
        while self._pending_otps:
            bearer, pending = next(iter(self._pending_otps.items()))
            if now - pending["created_at"] <= 300:
                break
            self._pending_otps.pop(bearer)
            try:
                await pending["backend"].disconnect()
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                logger.warning(
                    "Error disconnecting stale OTP backend {}: {}", bearer[:8], exc
                )
            removed += 1

        return removed

    async def shutdown(self) -> None:
        """Disconnect all active backends. Call on server shutdown."""
        for bearer, backend in list(self.active_clients.items()):
            try:
                await backend.disconnect()
            except Exception:
                logger.warning("Error disconnecting backend {}", bearer[:8])
        self.active_clients.clear()
        self.session_owners.clear()

        # Disconnect pending OTP backends
        for bearer, pending in list(self._pending_otps.items()):
            try:
                await pending["backend"].disconnect()
            except Exception:
                logger.warning("Error disconnecting pending OTP backend {}", bearer[:8])
        self._pending_otps.clear()
