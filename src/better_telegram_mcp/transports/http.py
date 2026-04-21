"""HTTP transport mode for better-telegram-mcp.

Multi-user mode: each bearer token maps to its own TelegramClient.
Auth endpoints handle bot registration and user OTP flow.
MCP endpoint requires Bearer auth and resolves per-user backend.

Single-user fallback: stored credentials via relay page (backward compat).
"""

from __future__ import annotations

import os
import sys
from contextvars import ContextVar

from loguru import logger
from mcp_core.relay.client import create_session, poll_for_result

from ..config import Settings
from ..relay_schema import RELAY_SCHEMA
from .credential_store import CredentialStore

DEFAULT_RELAY_URL = "https://better-telegram-mcp.n24q02m.com"

# ContextVar for per-user backend injection in multi-user HTTP mode
_current_backend: ContextVar = ContextVar("current_backend")


def get_current_backend():
    """Get the per-user backend from context (HTTP mode).

    Returns None if not in HTTP mode or no backend set.
    """
    return _current_backend.get(None)


async def setup_credentials(settings: Settings) -> dict[str, str]:
    """Obtain credentials via relay page and store them encrypted.

    Returns:
        Credential dict with keys like TELEGRAM_BOT_TOKEN, etc.

    Raises:
        RuntimeError: If relay setup fails or times out.
    """
    store = CredentialStore(settings.data_dir, secret=settings.secret)
    creds = store.load()

    if creds is not None:
        logger.info("Loaded stored credentials from {}", settings.data_dir)
        return creds

    # Need relay setup
    logger.info("No stored credentials found. Starting relay setup...")
    relay_url = DEFAULT_RELAY_URL

    try:
        session = await create_session(relay_url, "better-telegram-mcp", RELAY_SCHEMA)
    except Exception as exc:
        msg = (
            f"Cannot reach relay server at {relay_url}. "
            "Set credentials manually or check network."
        )
        raise RuntimeError(msg) from exc

    print(
        f"\nSetup required. Open this URL to configure:\n{session.relay_url}\n",
        file=sys.stderr,
        flush=True,
    )

    try:
        creds = await poll_for_result(relay_url, session)
    except RuntimeError as exc:
        msg = "Relay setup timed out or session expired"
        raise RuntimeError(msg) from exc

    store.store(creds)
    logger.info("Credentials stored successfully")
    return creds


def _is_multi_user_mode() -> bool:
    """Check if multi-user HTTP mode is configured."""
    return bool(
        os.environ.get("DCR_SERVER_SECRET")
        and os.environ.get("PUBLIC_URL")
        and os.environ.get("TELEGRAM_API_ID")
        and os.environ.get("TELEGRAM_API_HASH")
    )


def start_http(settings: Settings) -> None:
    """Start MCP server in HTTP mode.

    Three outcomes:
    - Full multi-user OAuth 2.1 when all four env vars are present
      (``DCR_SERVER_SECRET`` + ``PUBLIC_URL`` + ``TELEGRAM_API_ID`` +
      ``TELEGRAM_API_HASH``). Per-JWT-sub Telethon clients, isolated
      credentials, the intended public-deploy mode.
    - Single-user relay fallback when ``PUBLIC_URL`` is absent — that's
      self-host / localhost ``uvx`` usage and a single shared config is
      correct there.
    - ``RuntimeError`` when ``PUBLIC_URL`` is set but the other three env
      vars aren't. Without all four, the fallback would serve a shared
      ``default.session`` + shared ``TELEGRAM_PHONE`` on a public URL, and
      two concurrent visitors would overwrite each other's Telegram
      credentials (the 2026-04-21 incident). Refuse to start rather than
      silently ship that behaviour. Override with
      ``TELEGRAM_ACCEPT_SHARED_SINGLE_USER=1`` iff you really do own every
      request (e.g. a private CF Tunnel behind basic auth).
    """
    if _is_multi_user_mode():
        _start_multi_user_http(settings)
        return

    public_url = os.environ.get("PUBLIC_URL")
    override = os.environ.get("TELEGRAM_ACCEPT_SHARED_SINGLE_USER") == "1"
    if public_url and not override:
        missing = [
            name
            for name in (
                "DCR_SERVER_SECRET",
                "TELEGRAM_API_ID",
                "TELEGRAM_API_HASH",
            )
            if not os.environ.get(name)
        ]
        msg = (
            "Refusing to start: PUBLIC_URL is set (public deploy detected) "
            "but multi-user mode requires "
            f"{', '.join(missing)} to be set as well. Without them the server "
            "falls back to a SHARED default.session + TELEGRAM_PHONE across "
            "every visitor, which leaks credentials. Either provide the "
            "missing env vars to enable per-user OAuth 2.1, or set "
            "TELEGRAM_ACCEPT_SHARED_SINGLE_USER=1 to explicitly opt in to "
            "single-user behaviour (only safe on private networks)."
        )
        raise RuntimeError(msg)

    _start_single_user_http(settings)


def _start_single_user_http(settings: Settings) -> None:
    """Single-user HTTP mode: env vars > stored creds > relay setup.

    Backward compatible with the original HTTP transport.
    """
    import asyncio

    from ..server import mcp

    # If env vars already have credentials, skip CredentialStore/relay
    if not settings.is_configured:
        store = CredentialStore(settings.data_dir, secret=settings.secret)
        creds = store.load()

        if creds is None:
            creds = asyncio.run(setup_credentials(settings))

        # Apply credentials to environment so lifespan picks them up
        for key, value in creds.items():
            if key.startswith("TELEGRAM_") and key not in os.environ:
                os.environ[key] = value

    mcp.run(transport="streamable-http")


def _start_multi_user_http(settings: Settings) -> None:
    """Multi-user HTTP mode: per-user auth with standard OAuth 2.1."""

    import uvicorn

    from .oauth_server import create_app

    port = int(os.environ.get("PORT", "8080"))
    public_url = os.environ["PUBLIC_URL"]
    master_secret = settings.secret

    app = create_app(
        data_dir=settings.data_dir,
        public_url=public_url,
        master_secret=master_secret,
    )

    logger.info("Starting multi-user OAuth HTTP server on port {}", port)
    logger.info("Public URL: {}", public_url)

    # Default to 127.0.0.1 for safety; override via HOST env var (e.g. Docker sets HOST=0.0.0.0)
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port, log_level="info")
