"""Zero-env-config relay setup flow.

When no env vars are set, this module resolves config from the encrypted
config file or triggers the relay page setup to collect credentials from the
user via a browser-based form.
"""

from __future__ import annotations

import sys

from loguru import logger
from mcp_relay_core.relay.client import create_session, poll_for_result
from mcp_relay_core.storage.config_file import write_config
from mcp_relay_core.storage.resolver import resolve_config

from .relay_schema import RELAY_SCHEMA

DEFAULT_RELAY_URL = "https://better-telegram-mcp.n24q02m.com"
REQUIRED_FIELDS_BOT = ["TELEGRAM_BOT_TOKEN"]
REQUIRED_FIELDS_USER = ["TELEGRAM_API_ID", "TELEGRAM_API_HASH"]
ALL_POSSIBLE_FIELDS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_PHONE",
]


async def ensure_config() -> dict[str, str] | None:
    """Resolve config or trigger relay setup.

    Resolution order:
    1. Encrypted config file (~/.config/mcp/config.enc)
    2. Relay setup (browser-based form via relay server)

    Returns:
        Config dict with credential keys, or None if setup fails/times out.

    Note:
        Environment variables are NOT checked here -- pydantic-settings in
        Settings already handles that. This function is only called when
        Settings.is_configured is False (no env vars found).
    """
    # Check config file (skip env var check since pydantic-settings already did that)
    result = resolve_config("better-telegram-mcp", REQUIRED_FIELDS_BOT)
    if result.config is not None:
        logger.info("Config loaded from {}", result.source)
        return result.config

    # Also check user mode fields in config file
    result = resolve_config("better-telegram-mcp", REQUIRED_FIELDS_USER)
    if result.config is not None:
        logger.info("Config loaded from {}", result.source)
        return result.config

    # No config found -- trigger relay setup
    logger.info("No credentials found. Starting relay setup...")

    relay_url = DEFAULT_RELAY_URL
    try:
        session = await create_session(relay_url, "better-telegram-mcp", RELAY_SCHEMA)
    except Exception:
        logger.warning(
            "Cannot reach relay server at {}. "
            "Set TELEGRAM_BOT_TOKEN or TELEGRAM_API_ID + TELEGRAM_API_HASH manually.",
            relay_url,
        )
        return None

    # Log URL to stderr (visible to user in MCP client)
    print(
        f"\nSetup required. Open this URL to configure:\n{session.relay_url}\n",
        file=sys.stderr,
        flush=True,
    )

    # Poll for result
    try:
        config = await poll_for_result(relay_url, session)
    except RuntimeError:
        logger.error("Relay setup timed out or session expired")
        return None

    # Save to config file
    write_config("better-telegram-mcp", config)
    logger.info("Config saved successfully")
    return config
