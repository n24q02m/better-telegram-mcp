"""Credential resolution for better-telegram-mcp.

Resolution order (relay only when ALL local sources are empty):
1. ENV VARS          -- TELEGRAM_BOT_TOKEN or API_ID+API_HASH (checked by caller)
2. RELAY CONFIG      -- Saved from previous relay setup (~/.config/mcp/config.enc)
3. LOCAL CREDENTIALS -- Saved Telethon session files (~/.better-telegram-mcp/*.session)
4. RELAY SETUP       -- Interactive, ONLY when steps 1-2-3 are ALL empty
5. DEGRADED MODE     -- No Telegram tools
"""

from __future__ import annotations

import sys
from pathlib import Path

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


def check_saved_sessions() -> bool:
    """Check for saved Telethon session files from a previous authentication.

    Looks for *.session files in ~/.better-telegram-mcp/. If found, the user
    has previously authenticated and only needs to provide api_id + api_hash
    to reuse the saved session (no re-authentication required).

    Returns:
        True if at least one session file exists, False otherwise.
    """
    data_dir = Path.home() / ".better-telegram-mcp"
    if not data_dir.exists():
        return False
    sessions = list(data_dir.glob("*.session"))
    return len(sessions) > 0


async def ensure_config() -> dict[str, str] | None:
    """Resolve config: config file -> saved sessions -> relay setup -> degraded.

    Relay is ONLY triggered when steps 1-2-3 are ALL empty (first-time setup).

    Resolution order (env vars already checked by caller via Settings.is_configured):
    1. Encrypted config file (~/.config/mcp/config.enc)
    2. Saved Telethon session files (~/.better-telegram-mcp/*.session)
    3. Relay setup (interactive, only when no local credentials exist)
    4. Degraded mode (no Telegram tools)

    Returns:
        Config dict with credential keys, or None if setup fails/skipped.
    """
    from mcp_relay_core.storage.resolver import resolve_config

    # 1. Check saved relay config file (bot mode)
    result = resolve_config(SERVER_NAME, REQUIRED_FIELDS_BOT)
    if result.config is not None:
        logger.info("Config loaded from {}", result.source)
        return result.config

    # Also check user mode fields in config file
    result = resolve_config(SERVER_NAME, REQUIRED_FIELDS_USER)
    if result.config is not None:
        logger.info("Config loaded from {}", result.source)
        return result.config

    # 2. Check saved Telethon session files (local credentials)
    if check_saved_sessions():
        logger.info(
            "Found saved Telethon session files. "
            "Set TELEGRAM_API_ID + TELEGRAM_API_HASH to reuse them "
            "(no re-authentication needed)."
        )
        return None

    # 3. No local credentials found -- trigger relay setup
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
            logger.info("Relay setup skipped by user.")
        elif "timed out" in str(e).lower():
            logger.info("Relay setup timed out.")
        else:
            logger.error("Relay setup failed: {}", e)

        logger.info("Telegram tools will be unavailable.")
        return None
