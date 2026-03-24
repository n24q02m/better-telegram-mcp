"""Auth client that polls a remote relay server for OTP commands.

Used when TELEGRAM_AUTH_URL is a remote URL (not "local").
MCP local creates a session on the remote server, then polls for
commands (send_code, verify) and executes them via Telethon locally.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import httpx
import typer
from loguru import logger

if TYPE_CHECKING:
    from .backends.base import TelegramBackend
    from .config import Settings

POLL_INTERVAL = 2  # seconds


def _mask_phone(phone: str) -> str:
    if len(phone) > 7:
        return phone[:4] + "***" + phone[-4:]
    return phone[:2] + "***"


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
            json={"phone_masked": _mask_phone(phone)},
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


app = typer.Typer(help="Better Telegram MCP Auth Client CLI")


@app.command()
def main() -> None:
    """Run the auth client."""
    from better_telegram_mcp.config import Settings

    settings = Settings()
    if settings.mode == "bot":
        typer.echo("Auth client is only needed for user mode.", err=True)
        raise typer.Exit(1)

    if not settings.phone:
        typer.echo("TELEGRAM_PHONE must be set in your configuration.", err=True)
        raise typer.Exit(1)

    async def _run() -> None:
        from better_telegram_mcp.backends.user_backend import UserBackend

        backend = UserBackend(settings)
        await backend.connect()

        if await backend.is_authorized():
            typer.echo("Already authorized!")
            await backend.disconnect()
            return

        client = AuthClient(backend, settings)
        url = await client.create_session()
        typer.echo(f"Auth session created! Please open: {url}")
        typer.echo("Waiting for authentication commands from relay server...")

        import webbrowser

        try:
            # Use to_thread to avoid blocking if we were in a running loop,
            # though here we are the main loop.
            await asyncio.to_thread(webbrowser.open, url)
        except Exception:
            pass

        auth_task = asyncio.create_task(client.poll_and_execute())
        await client.wait_for_auth()
        await auth_task
        await client.close()
        await backend.disconnect()
        typer.echo("Authentication successful!")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
