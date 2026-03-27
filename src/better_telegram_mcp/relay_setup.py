"""Relay-first setup flow for better-telegram-mcp.

Always shows the relay URL at startup so users can configure Telegram
credentials via browser. If the user skips, the server starts in
degraded mode (help and config tools only).

Resolution order:
1. Environment variables (checked by pydantic Settings before calling this)
2. Encrypted config file (~/.config/mcp/config.enc)
3. Relay setup (browser-based form via relay server)
4. Degraded mode (no Telegram tools)
"""

from __future__ import annotations

import sys

from loguru import logger

from .relay_schema import RELAY_SCHEMA

DEFAULT_RELAY_URL = "https://better-telegram-mcp.n24q02m.com"
SERVER_NAME = "better-telegram-mcp"
REQUIRED_FIELDS_BOT = ["TELEGRAM_BOT_TOKEN"]
REQUIRED_FIELDS_USER = ["TELEGRAM_API_ID", "TELEGRAM_API_HASH"]
ALL_POSSIBLE_FIELDS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_PHONE",
]


async def ensure_config() -> dict[str, str] | None:
    """Resolve config or trigger relay setup (relay-first design).

    Resolution order:
    1. Encrypted config file (~/.config/mcp/config.enc)
    2. Relay setup (browser-based form via relay server)

    Returns:
        Config dict with credential keys, or None if setup fails/skipped.

    Note:
        Environment variables are NOT checked here -- pydantic-settings in
        Settings already handles that. This function is only called when
        Settings.is_configured is False (no env vars found).
    """
    from mcp_relay_core.storage.resolver import resolve_config

    # Check config file (skip env var check since pydantic-settings already did that)
    result = resolve_config(SERVER_NAME, REQUIRED_FIELDS_BOT)
    if result.config is not None:
        logger.info("Config loaded from {}", result.source)
        return result.config

    # Also check user mode fields in config file
    result = resolve_config(SERVER_NAME, REQUIRED_FIELDS_USER)
    if result.config is not None:
        logger.info("Config loaded from {}", result.source)
        return result.config

    # No config found -- always trigger relay setup (relay-first)
    logger.info("No credentials found. Starting relay setup...")

    relay_url = DEFAULT_RELAY_URL
    try:
        from mcp_relay_core.relay.client import create_session

        session = await create_session(relay_url, SERVER_NAME, RELAY_SCHEMA)
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
        from mcp_relay_core.relay.client import poll_for_result
        from mcp_relay_core.storage.config_file import write_config

        config = await poll_for_result(relay_url, session)

        # Save to config file
        write_config(SERVER_NAME, config)
        logger.info("Config saved successfully")
        return config

    except RuntimeError as e:
        if "RELAY_SKIPPED" in str(e):
            logger.info(
                "Relay setup skipped by user. Telegram tools will be unavailable."
            )
        elif "timed out" in str(e).lower():
            logger.info("Relay setup timed out")
        else:
            logger.error("Relay setup failed: {}", e)
        return None
