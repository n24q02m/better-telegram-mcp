"""Auth client that polls a remote relay server for OTP commands.

Used when TELEGRAM_AUTH_URL is a remote URL (not "local").
MCP local creates a session on the remote server, then polls for
commands (send_code, verify) and executes them via Telethon locally.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger

from .utils.formatting import mask_phone

if TYPE_CHECKING:
    from .backends.base import TelegramBackend
    from .config import Settings

POLL_INTERVAL = 2  # seconds


class AuthClient:
    """Client that communicates with a remote auth relay server."""

    def __init__(self, backend: TelegramBackend, settings: Settings):
        self._backend = backend
        self._settings = settings
        self._auth_complete = asyncio.Event()
        self._base_url = settings.auth_url.rstrip("/")

        # Validate auth_url to prevent SSRF
        from .backends.security import validate_url

        validate_url(self._base_url)

        self._client = httpx.AsyncClient(timeout=10.0)
        self.url: str = ""  # auth page URL for user

    async def create_session(self) -> str:
        """Create auth session on remote server. Returns auth page URL."""
        phone = self._settings.phone or ""
        resp = await self._client.post(
            f"{self._base_url}/api/sessions",
            json={"phone_masked": mask_phone(phone)},
        )
        resp.raise_for_status()
        data = resp.json()
        self.url = data["url"]
        self._token = data["token"]
        logger.info("Auth session created: {}", self.url)
        return self.url

    async def poll_and_execute(self) -> None:
        """Poll remote server for commands and execute them locally."""
        while not self._auth_complete.is_set():
            await asyncio.sleep(POLL_INTERVAL)
            try:
                resp = await self._client.get(
                    f"{self._base_url}/api/sessions/{self._token}"
                )
                data = resp.json()

                if data["status"] == "expired":
                    logger.warning("Auth session expired")
                    break

                if data["status"] == "completed":
                    self._auth_complete.set()
                    break

                if data["status"] == "command":
                    await self._handle_command(data)

            except httpx.HTTPError as e:
                logger.debug("Poll error: {}", e)
            except Exception as e:
                logger.debug("Poll error: {}", e)

    async def _handle_command(self, cmd: dict[str, Any]) -> None:
        """Execute a command from the relay server via local Telethon."""
        action = cmd.get("action")
        phone = self._settings.phone

        if action == "send_code" and phone:
            try:
                await self._backend.send_code(phone)
                await self._push_result("send_code", ok=True)
            except Exception as e:
                await self._push_result("send_code", ok=False, error=str(e))

        elif action == "verify" and phone:
            code = cmd.get("code", "")
            password = cmd.get("password")
            try:
                result = await self._backend.sign_in(phone, code, password=password)
                name = result.get("authenticated_as", "User")
                await self._push_result("verify", ok=True, name=name)
                self._auth_complete.set()
            except Exception as e:
                await self._push_result("verify", ok=False, error=str(e))

    async def _push_result(self, action: str, **kwargs: Any) -> None:
        """Push command result back to relay server."""
        try:
            await self._client.post(
                f"{self._base_url}/api/sessions/{self._token}/result",
                json={"action": action, **kwargs},
            )
        except Exception as e:
            logger.debug("Push result error: {}", e)

    async def wait_for_auth(self) -> None:
        """Block until authentication is complete."""
        await self._auth_complete.wait()

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()
