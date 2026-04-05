"""Credential resolution for better-telegram-mcp.

Resolution order (relay only when ALL local sources are empty):
1. ENV VARS          -- TELEGRAM_BOT_TOKEN or API_ID+API_HASH (checked by caller)
2. RELAY CONFIG      -- Saved from previous relay setup (~/.config/mcp/config.enc)
3. LOCAL CREDENTIALS -- Saved Telethon session files (~/.better-telegram-mcp/*.session)
4. RELAY SETUP       -- Interactive, ONLY when steps 1-2-3 are ALL empty
5. DEGRADED MODE     -- No Telegram tools
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from .relay_schema import RELAY_SCHEMA

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

# Error sanitization patterns (same as auth_server.py for consistency)
_CAUSED_BY_RE = re.compile(r"\s*\(caused by \w+\)\s*$", re.IGNORECASE)
_ERROR_SIMPLIFICATIONS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r".*password.*required.*", re.IGNORECASE),
        "Two-factor authentication password is required.",
    ),
    (
        re.compile(r".*password.*invalid.*|.*invalid.*password.*", re.IGNORECASE),
        "Incorrect 2FA password. Please try again.",
    ),
    (
        re.compile(r".*phone.*code.*invalid.*|.*invalid.*code.*", re.IGNORECASE),
        "Invalid OTP code. Please check and try again.",
    ),
    (
        re.compile(r".*phone.*code.*expired.*|.*code.*expired.*", re.IGNORECASE),
        "OTP code has expired. Please request a new one.",
    ),
    (
        re.compile(r".*flood.*wait.*|.*too many.*", re.IGNORECASE),
        "Too many attempts. Please wait a moment and try again.",
    ),
]


def _sanitize_error(msg: str) -> str:
    """Simplify internal error messages to user-friendly text."""
    cleaned = _CAUSED_BY_RE.sub("", msg).strip()
    for pattern, friendly in _ERROR_SIMPLIFICATIONS:
        if pattern.match(cleaned):
            return friendly
    return cleaned


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


def _resolve_local_config() -> dict[str, str] | None:
    """Check for existing config in encrypted files (bot and user modes)."""
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

    return None


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
                "text": f"Failed to send OTP code: {_sanitize_error(str(e))}",
            },
        )
        return False

    # Step 2: Ask user for OTP code via relay
    otp_message_id = await send_message(
        relay_url,
        session_id,
        {
            "type": "input_required",
            "text": "Enter the OTP code sent to your Telegram app",
            "data": {"field": "otp_code", "input_type": "text", "placeholder": "12345"},
        },
    )

    try:
        otp_code = await poll_for_responses(
            relay_url,
            session_id,
            otp_message_id,
            timeout_s=300.0,
        )
    except RuntimeError:
        await send_message(
            relay_url,
            session_id,
            {
                "type": "error",
                "text": "Timed out waiting for OTP code.",
            },
        )
        return False

    # Step 3: Try sign in with OTP code
    try:
        result = await backend.sign_in(phone, otp_code.strip())
        name = result.get("authenticated_as", "User")
        await send_message(
            relay_url,
            session_id,
            {
                "type": "complete",
                "text": f"Authenticated as {name}. Session saved. You can close this tab.",
            },
        )
        return True
    except Exception as e:
        error_msg = str(e)
        if not _needs_2fa_password(error_msg):
            # Not a 2FA error -- sign-in failed for another reason
            await send_message(
                relay_url,
                session_id,
                {
                    "type": "error",
                    "text": f"Authentication failed: {_sanitize_error(error_msg)}",
                },
            )
            return False

    # Step 4: 2FA password required -- ask user
    password_message_id = await send_message(
        relay_url,
        session_id,
        {
            "type": "input_required",
            "text": "Your account has two-factor authentication. Enter your 2FA password.",
            "data": {
                "field": "2fa_password",
                "input_type": "password",
                "placeholder": "",
            },
        },
    )

    try:
        password = await poll_for_responses(
            relay_url,
            session_id,
            password_message_id,
            timeout_s=300.0,
        )
    except RuntimeError:
        await send_message(
            relay_url,
            session_id,
            {
                "type": "error",
                "text": "Timed out waiting for 2FA password.",
            },
        )
        return False

    # Step 5: Sign in with 2FA password
    try:
        result = await backend.sign_in(phone, otp_code.strip(), password=password)
        name = result.get("authenticated_as", "User")
        await send_message(
            relay_url,
            session_id,
            {
                "type": "complete",
                "text": f"Authenticated as {name}. Session saved. You can close this tab.",
            },
        )
        return True
    except Exception as e:
        await send_message(
            relay_url,
            session_id,
            {
                "type": "error",
                "text": f"Authentication failed: {_sanitize_error(str(e))}",
            },
        )
        return False


async def _initiate_relay_session(relay_url: str):
    """Create a relay session and open the setup URL in the browser."""
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
    import webbrowser

    asyncio.get_event_loop().run_in_executor(
        None, lambda: webbrowser.open(session.relay_url)
    )
    return session


async def _run_user_auth_flow(relay_url: str, session_id: str, config: dict[str, str]):
    """Handle UserBackend authentication flow after receiving relay config."""
    from .config import Settings
    from .backends.user_backend import UserBackend

    settings = Settings.from_relay_config(config)
    backend = UserBackend(settings)
    await backend.connect()

    try:
        if not await backend.is_authorized():
            from mcp_relay_core.relay.client import send_message

            await send_message(
                relay_url,
                session_id,
                {
                    "type": "info",
                    "text": "Credentials saved. Starting Telegram authentication...",
                },
            )

            auth_ok = await _relay_telethon_auth(
                relay_url,
                session_id,
                backend,
                settings,
            )
            if not auth_ok:
                logger.warning("Relay Telethon auth failed. User can retry later.")
        else:
            # Already authorized (existing session file)
            from mcp_relay_core.relay.client import send_message

            await send_message(
                relay_url,
                session_id,
                {
                    "type": "complete",
                    "text": "Telegram config saved. Session already authorized!",
                },
            )
    finally:
        await backend.disconnect()


async def _poll_and_finalize_config(relay_url: str, session) -> dict[str, str] | None:
    """Poll for relay result, save config, and trigger completion/auth flow."""
    try:
        from mcp_relay_core.relay.client import poll_for_result
        from mcp_relay_core.storage.config_file import write_config

        config = await poll_for_result(relay_url, session)

        # Save to config file
        write_config(SERVER_NAME, config)
        logger.info("Config saved successfully")

        # For user mode: run Telethon OTP/2FA auth via relay messaging
        if _is_user_mode_config(config):
            await _run_user_auth_flow(relay_url, session.session_id, config)
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
    # 1. Check local config (encrypted files)
    config = _resolve_local_config()
    if config:
        return config

    # 2. Check saved Telethon session files
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
    session = await _initiate_relay_session(relay_url)
    if not session:
        return None

    # 4. Poll for result and finalize
    return await _poll_and_finalize_config(relay_url, session)
