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


# ---------------------------------------------------------------------------
def _resolve_local_config() -> dict[str, str] | None | str:
    """Check for existing config in files or session caches.

    Returns:
        The config dictionary if found, "SESSION_EXISTS" if local sessions exist,
        or None otherwise.
    """
    from mcp_relay_core.storage.resolver import resolve_config

    # 1. Check saved relay config file (bot then user mode)
    for fields in [REQUIRED_FIELDS_BOT, REQUIRED_FIELDS_USER]:
        result = resolve_config(SERVER_NAME, fields)
        if result.config is not None:
            logger.info("Config loaded from {}", result.source)
            return result.config

    # 2. Check saved Telethon session files
    if check_saved_sessions():
        logger.info(
            "Found saved Telethon session files. Set TELEGRAM_PHONE to reuse them."
        )
        return "SESSION_EXISTS"
    return None


# ---------------------------------------------------------------------------
async def _initiate_relay_session(relay_url: str):
    """Create a new relay session and open the browser.

    Args:
        relay_url: The URL of the relay server.

    Returns:
        The created session object, or None if the relay is unreachable.
    """
    try:
        from mcp_relay_core.relay.client import create_session

        session = await create_session(relay_url, SERVER_NAME, RELAY_SCHEMA)
    except Exception:
        logger.warning("Cannot reach relay server at {}.", relay_url)
        return None

    print(
        f"\nSetup required. Open this URL to configure:\n{session.relay_url}\n",
        file=sys.stderr,
        flush=True,
    )

    import asyncio
    import webbrowser

    asyncio.get_event_loop().run_in_executor(
        None, lambda: webbrowser.open(session.relay_url)
    )
    return session


# ---------------------------------------------------------------------------
async def _run_user_auth_flow(relay_url: str, session_id: str, config: dict[str, str]):
    """Connect UserBackend and perform Telethon OTP/2FA if needed.

    Args:
        relay_url: The URL of the relay server.
        session_id: The ID of the current relay session.
        config: The configuration dictionary retrieved from the relay.
    """
    from .backends.user_backend import UserBackend
    from .config import Settings

    settings = Settings.from_relay_config(config)
    backend = UserBackend(settings)
    await backend.connect()
    try:
        if not await backend.is_authorized():
            from mcp_relay_core.relay.client import send_message

            await send_message(
                relay_url,
                session_id,
                {"type": "info", "text": "Starting Telegram authentication..."},
            )
            await _relay_telethon_auth(relay_url, session_id, backend, settings)
        else:
            from mcp_relay_core.relay.client import send_message

            await send_message(
                relay_url,
                session_id,
                {"type": "complete", "text": "Session already authorized!"},
            )
    finally:
        await backend.disconnect()


# ---------------------------------------------------------------------------
async def _poll_and_finalize_config(relay_url: str, session) -> dict[str, str]:
    """Wait for relay results, save them, and trigger post-setup actions.

    Args:
        relay_url: The URL of the relay server.
        session: The current relay session object.

    Returns:
        The finalized configuration dictionary.
    """
    from mcp_relay_core.relay.client import poll_for_result, send_message
    from mcp_relay_core.storage.config_file import write_config

    config = await poll_for_result(relay_url, session)
    write_config(SERVER_NAME, config)
    logger.info("Config saved successfully")

    if _is_user_mode_config(config):
        await _run_user_auth_flow(relay_url, session.session_id, config)
    else:
        try:
            await send_message(
                relay_url,
                session.session_id,
                {"type": "complete", "text": "Setup complete!"},
            )
        except Exception:
            pass
    return config


# ---------------------------------------------------------------------------
async def ensure_config() -> dict[str, str] | None:
    """Resolve config: config file -> saved sessions -> relay setup -> degraded."""
    local_res = _resolve_local_config()
    if local_res == "SESSION_EXISTS":
        return None
    if local_res is not None:
        return local_res

    logger.info("No credentials found. Starting relay setup...")
    relay_url = DEFAULT_RELAY_URL
    session = await _initiate_relay_session(relay_url)
    if not session:
        return None

    try:
        return await _poll_and_finalize_config(relay_url, session)
    except RuntimeError as e:
        msg = str(e).lower()
        if "skipped" in msg:
            logger.info("Relay setup skipped by user.")
        elif "timed out" in msg:
            logger.info("Relay setup timed out.")
        else:
            logger.error("Relay setup failed: {}", e)
        return None
