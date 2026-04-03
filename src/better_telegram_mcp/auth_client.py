"""Auth client that polls a remote relay server for OTP commands.

Used when TELEGRAM_AUTH_URL is a remote URL (not "local").
MCP local creates a session on the remote server, then polls for
commands (send_code, verify) and executes them via Telethon locally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from loguru import logger

from .utils.formatting import _mask_phone

if TYPE_CHECKING:
    from .backends.base import TelegramBackend
    from .config import Settings

POLL_INTERVAL = 2  # seconds


class AuthClient:
    """Client that communicates with a remote auth relay server."""

    def __init__(self, backend: TelegramBackend, settings: Settings):
        self._backend = backend
        self._settings = settings
        self._base_url = settings.auth_url
        self._client = httpx.AsyncClient(timeout=30)
        self._token: str | None = None
        self.url: str | None = None

    async def create_session(self) -> str:
        """Create auth session on remote server. Returns auth page URL."""
        phone = self._settings.phone or ""
        resp = await self._client.post(
            f"{self._base_url}/api/sessions",
            json={"phone_masked": _mask_phone(phone)},
        )
        resp.raise_for_status()
        data = resp.json()
        self.url = data["url"]
        self._token = data["token"]
        return self.url

    async def poll_and_execute(self) -> None:
        """Poll relay for pending commands and execute them locally."""
        if not self._token:
            return

        try:
            resp = await self._client.get(
                f"{self._base_url}/api/sessions/{self._token}/command"
            )
            if resp.status_code == 204:  # No command
                return

            resp.raise_for_status()
            cmd = resp.json()

            action = cmd["action"]
            phone = self._settings.phone or ""
            if action == "send_code":
                try:
                    await self._backend.send_code(phone)
                    await self._send_result("ok")
                except Exception as e:
                    logger.error(f"Failed to send code: {e}")
                    await self._send_result("error", str(e))

            elif action == "verify":
                code = cmd.get("code")
                password = cmd.get("password")
                if not code:
                    return

                try:
                    await self._backend.sign_in(phone, code, password=password)
                    await self._send_result("ok")
                except Exception as e:
                    logger.error(f"Failed to verify: {e}")
                    await self._send_result("error", str(e))

        except Exception as e:
            logger.exception(f"Polling error: {e}")

    async def _send_result(
        self, status: str, error: str | None = None
    ) -> None:
        """Report execution result back to relay."""
        if not self._token:
            return

        payload = {"status": status}
        if error:
            payload["error"] = error

        await self._client.post(
            f"{self._base_url}/api/sessions/{self._token}/result",
            json=payload,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()
