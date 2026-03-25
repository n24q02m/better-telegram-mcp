"""HTTP transport mode for better-telegram-mcp.

Starts the MCP server as an HTTP endpoint using FastMCP's streamable HTTP.
Credentials are received via relay page and stored encrypted on server.
"""

from __future__ import annotations

import sys

from loguru import logger
from mcp_relay_core.relay.client import create_session, poll_for_result

from ..config import Settings
from ..relay_schema import RELAY_SCHEMA
from .credential_store import CredentialStore

DEFAULT_RELAY_URL = "https://better-telegram-mcp.n24q02m.com"


async def setup_credentials(settings: Settings) -> dict[str, str]:
    """Obtain credentials via relay page and store them encrypted.

    Returns:
        Credential dict with keys like TELEGRAM_BOT_TOKEN, etc.

    Raises:
        RuntimeError: If relay setup fails or times out.
    """
    store = CredentialStore(settings.data_dir)
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


def start_http(settings: Settings) -> None:
    """Start MCP server in HTTP mode.

    This is a synchronous entry point that:
    1. Checks for stored credentials (or triggers relay setup)
    2. Applies credentials to settings
    3. Runs FastMCP with streamable-http transport
    """
    import asyncio

    from ..server import mcp

    # Setup credentials if needed
    store = CredentialStore(settings.data_dir)
    creds = store.load()

    if creds is None:
        # Run async setup synchronously before starting the server
        creds = asyncio.run(setup_credentials(settings))

    # Apply credentials to environment so lifespan picks them up
    import os

    for key, value in creds.items():
        if key.startswith("TELEGRAM_") and key not in os.environ:
            os.environ[key] = value

    # Run FastMCP in HTTP mode
    mcp.run(transport="streamable-http")
