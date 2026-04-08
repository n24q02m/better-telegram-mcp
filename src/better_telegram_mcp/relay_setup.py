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
from typing import TYPE_CHECKING

from loguru import logger

from .relay_schema import RELAY_SCHEMA
from .utils.formatting import sanitize_error

if TYPE_CHECKING:
    from .backends.user_backend import UserBackend
    from .config import Settings

DEFAULT_RELAY_URL = "https://better-telegram-mcp.n24q02m.com"
SERVER_NAME = "better-telegram-mcp"
REQUIRED_FIELDS_BOT = ["TELEGRAM_BOT_TOKEN"]
REQUIRED_FIELDS_USER = ["TELEGRAM_PHONE"]
ALL_POSSIBLE_FIELDS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_PHONE",
]


def _needs_2fa_password(error_msg: str) -> bool:
    """Check if the error indicates 2FA password is required."""
    return any(
        kw in error_msg.lower() for kw in ("password", "2fa", "two-factor", "srp")
    )


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


def _is_user_mode_config(config: dict[str, str]) -> bool:
    """Check if config has user-mode credentials (phone number).

    API ID and API Hash have built-in defaults in config.py, so only phone
    is needed from relay to identify user mode.
    """
    return bool(config.get("TELEGRAM_PHONE"))


async def _relay_telethon_auth(
    relay_url: str,
    session_id: str,
    backend: UserBackend,
    settings: Settings,
) -> bool:
    """Run Telethon OTP/2FA auth flow via relay bidirectional messaging.

    Uses send_message(type='input_required') for user input and
    poll_for_responses() to receive OTP code and optional 2FA password.

    Args:
        relay_url: Base URL of the relay server.
        session_id: Active relay session ID.
        backend: Connected UserBackend instance.
        settings: Settings with phone number.

    Returns:
        True if authentication succeeded, False otherwise.
    """
    from mcp_relay_core.relay.client import poll_for_responses, send_message

    phone = settings.phone
    if not phone:
        await send_message(
            relay_url,
            session_id,
            {
                "type": "error",
                "text": "Phone number is required for user mode authentication.",
            },
        )
        return False

    # Step 1: Send OTP code to Telegram
    try:
        await send_message(
            relay_url,
            session_id,
            {
                "type": "info",
                "text": "Sending OTP code to your Telegram app...",
            },
        )
        await backend.send_code(phone)
    except Exception as e:
        await send_message(
            relay_url,
            session_id,
            {
                "type": "error",
                "text": f"Failed to send code: {sanitize_error(str(e))}",
            },
        )
        return False

    # Step 2: Request OTP code from user via relay
    try:
        msg_resp = await send_message(
            relay_url,
            session_id,
            {
                "type": "input_required",
                "label": "Telegram OTP Code",
                "placeholder": "12345",
                "help": f"Check your Telegram app for a code sent to {phone}",
            },
        )
        # Handle both old (string) and new (object with message_id) responses
        msg_id = getattr(msg_resp, "message_id", "")
        code = await poll_for_responses(relay_url, session_id, msg_id)
        if not code:
            return False

        # Step 3: Sign in
        try:
            await backend.sign_in(phone, code)
            await send_message(
                relay_url,
                session_id,
                {
                    "type": "complete",
                    "text": "Telegram user authentication successful! Setup complete.",
                },
            )
            return True
        except Exception as e:
            error_msg = str(e)
            if not _needs_2fa_password(error_msg):
                await send_message(
                    relay_url,
                    session_id,
                    {
                        "type": "error",
                        "text": f"Authentication failed: {sanitize_error(error_msg)}",
                    },
                )
                return False

            # Step 4: Request 2FA password via relay
            msg_resp = await send_message(
                relay_url,
                session_id,
                {
                    "type": "input_required",
                    "label": "Two-Factor Password",
                    "placeholder": "Your 2FA password",
                    "help": "Your account has 2FA enabled. Please enter your password.",
                    "is_password": True,
                },
            )
            msg_id = getattr(msg_resp, "message_id", "")
            password = await poll_for_responses(relay_url, session_id, msg_id)
            if not password:
                return False

            try:
                await backend.sign_in(phone, code, password=password)
                await send_message(
                    relay_url,
                    session_id,
                    {
                        "type": "complete",
                        "text": "Telegram user authentication successful! Setup complete.",
                    },
                )
                return True
            except Exception as e2:
                await send_message(
                    relay_url,
                    session_id,
                    {
                        "type": "error",
                        "text": f"2FA authentication failed: {sanitize_error(str(e2))}",
                    },
                )
                return False

    except Exception as e:
        logger.error("Relay authentication flow error: {}", e)
        return False


async def ensure_config() -> dict[str, str] | None:
    """Resolve config: config file -> saved sessions -> relay setup -> degraded.

    Relay is ONLY triggered when steps 1-2-3 are ALL empty (first-time setup).
    For user mode, also handles Telethon OTP/2FA auth via relay messaging.

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
            "Set TELEGRAM_PHONE to reuse them "
            "(API credentials have built-in defaults, no re-authentication needed)."
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
            "Set TELEGRAM_BOT_TOKEN or TELEGRAM_PHONE manually.",
            relay_url,
        )
        return None

    # Log URL to stderr (visible to user in MCP client)
    print(
        f"\nSetup required. Open this URL to configure:\n{session.relay_url}\n",
        file=sys.stderr,
        flush=True,
    )

    # Open browser automatically (non-blocking, best-effort)
    import asyncio

    from mcp_relay_core import try_open_browser

    try_open_browser(session.relay_url)

    # Poll for result
    try:
        from mcp_relay_core.relay.client import poll_for_result
        from mcp_relay_core.storage.config_file import write_config

        config = await poll_for_result(relay_url, session)

        # Save to config file
        write_config(SERVER_NAME, config)
        logger.info("Config saved successfully")

        # For user mode: run Telethon OTP/2FA auth via relay messaging
        if _is_user_mode_config(config):
            from .config import Settings

            settings = Settings.from_relay_config(config)

            from .backends.user_backend import UserBackend

            backend = UserBackend(settings)
            await backend.connect()

            try:
                if not await backend.is_authorized():
                    from mcp_relay_core.relay.client import send_message

                    await send_message(
                        relay_url,
                        session.session_id,
                        {
                            "type": "info",
                            "text": "Credentials saved. Starting Telegram authentication...",
                        },
                    )

                    auth_ok = await _relay_telethon_auth(
                        relay_url,
                        session.session_id,
                        backend,
                        settings,
                    )
                    if not auth_ok:
                        logger.warning(
                            "Relay Telethon auth failed. User can retry later."
                        )
                else:
                    # Already authorized (existing session file)
                    from mcp_relay_core.relay.client import send_message

                    await send_message(
                        relay_url,
                        session.session_id,
                        {
                            "type": "complete",
                            "text": "Telegram config saved. Session already authorized!",
                        },
                    )
            finally:
                await backend.disconnect()
        else:
            # Bot mode: just notify completion
            try:
                from mcp_relay_core.relay.client import send_message

                await send_message(
                    relay_url,
                    session.session_id,
                    {
                        "type": "complete",
                        "text": "Telegram config saved. Setup complete!",
                    },
                )
            except Exception:
                pass

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
