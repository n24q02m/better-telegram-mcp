"""Non-blocking credential state management for better-telegram-mcp.

State machine: awaiting_setup -> setup_in_progress -> (configured)
Reset: configured -> awaiting_setup (via setup tool)

Unlike wet-mcp, telegram has NO local fallback -- all tools need credentials.
When state is AWAITING_SETUP, tools return a clear error with setup URL.

Hot-reload: after relay saves credentials, the on_configured callback
(registered by server.py) reinitializes the Telegram backend so tools
work immediately without restart.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from enum import Enum

from loguru import logger

from .relay_setup import (
    DEFAULT_RELAY_URL,
    REQUIRED_FIELDS_BOT,
    REQUIRED_FIELDS_USER,
    SERVER_NAME,
    _needs_2fa_password,
    _sanitize_error,
    check_saved_sessions,
)

# All credential keys that indicate a configured state
CREDENTIAL_KEYS_BOT = REQUIRED_FIELDS_BOT  # ["TELEGRAM_BOT_TOKEN"]
CREDENTIAL_KEYS_USER = REQUIRED_FIELDS_USER  # ["TELEGRAM_PHONE"]


class CredentialState(Enum):
    AWAITING_SETUP = "awaiting_setup"
    SETUP_IN_PROGRESS = "setup_in_progress"
    CONFIGURED = "configured"


# Module-level state
_state = CredentialState.AWAITING_SETUP
_setup_url: str | None = None
_on_configured_callback: Callable[[], Awaitable[None]] | None = None

# Multi-step auth state (single-user local mode)
_step_backend: object | None = None  # UserBackend instance held during OTP flow
_step_phone: str = ""
_step_otp_code: str | None = None  # OTP code remembered for 2FA signin retry


async def _connect_and_send_code(backend, phone: str) -> None:
    """Connect Telethon backend and send OTP code to the user's Telegram app."""
    await backend.connect()
    await backend.send_code(phone)


def get_state() -> CredentialState:
    """Return current credential state."""
    return _state


def get_setup_url() -> str | None:
    """Return current relay setup URL (if any)."""
    return _setup_url


def resolve_credential_state() -> CredentialState:
    """Fast, synchronous credential check. Called during lifespan startup.

    Checks (in order):
    1. ENV VARS -- if bot_token or (api_id + api_hash + phone) present, state = CONFIGURED
    2. CONFIG FILE -- if saved config has credential keys, apply to env, state = CONFIGURED
    3. SAVED SESSIONS -- if Telethon session files exist, state = CONFIGURED
       (user still needs api_id+api_hash but those have built-in defaults)
    4. NOTHING -- state = AWAITING_SETUP (server starts fast, relay triggered lazily)

    Returns new state. Takes <10ms.
    """
    global _state

    # 1. Check env vars -- bot mode
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.info("Bot token found in environment")
        _state = CredentialState.CONFIGURED
        return _state

    # 1b. Check env vars -- user mode (phone required, api_id/api_hash have defaults)
    if os.environ.get("TELEGRAM_PHONE"):
        logger.info("User mode credentials found in environment")
        _state = CredentialState.CONFIGURED
        return _state

    # 2. Check config file (bot mode fields)
    try:
        from mcp_core.storage.config_file import read_config

        saved = read_config(SERVER_NAME)
        if saved:
            has_bot = bool(saved.get("TELEGRAM_BOT_TOKEN"))
            has_user = bool(saved.get("TELEGRAM_PHONE"))
            if has_bot or has_user:
                # Apply to env vars so Settings picks them up
                for key, value in saved.items():
                    if value and key not in os.environ:
                        os.environ[key] = value
                logger.info("Config loaded from encrypted file")
                _state = CredentialState.CONFIGURED
                return _state
    except Exception:
        pass

    # 3. Check saved Telethon session files
    if check_saved_sessions():
        logger.info(
            "Found saved Telethon session files. "
            "Set TELEGRAM_PHONE to reuse them "
            "(API credentials have built-in defaults)."
        )
        # Session files exist but user still needs to set phone to enable user mode.
        # This is a soft signal -- we stay in AWAITING_SETUP so relay can help.
        _state = CredentialState.AWAITING_SETUP
        return _state

    # 4. Nothing found
    logger.info("No credentials found -- server starting in awaiting_setup mode")
    _state = CredentialState.AWAITING_SETUP
    return _state


async def trigger_relay_setup(
    *, force: bool = False, timeout: float | None = None
) -> str | None:
    """Start relay session (lazy trigger). Returns setup URL or None.

    Uses SessionLock to reuse existing sessions across parallel processes.
    Tries to open browser automatically.
    Does NOT block -- returns URL immediately for the tool to include in response.
    """
    global _state, _setup_url

    if not force and _state not in (CredentialState.AWAITING_SETUP,):
        return _setup_url

    _state = CredentialState.SETUP_IN_PROGRESS

    try:
        # Check for existing session via lock
        from mcp_core import acquire_session_lock

        existing = await acquire_session_lock(SERVER_NAME)
        if existing:
            _setup_url = existing.relay_url
            logger.info("Reusing existing relay session")
            return _setup_url

        # Create new session
        from mcp_core.relay.client import create_session

        from .relay_schema import RELAY_SCHEMA

        relay_base = os.environ.get("MCP_RELAY_URL", DEFAULT_RELAY_URL)
        session = await create_session(relay_base, SERVER_NAME, RELAY_SCHEMA)  # ty: ignore[invalid-argument-type]

        # Save session lock for parallel processes
        import time

        from mcp_core import SessionInfo, write_session_lock

        await write_session_lock(
            SERVER_NAME,
            SessionInfo(
                session_id=session.session_id,
                relay_url=session.relay_url,
                created_at=time.time(),
            ),
        )

        _setup_url = session.relay_url

        # Try to open browser (best-effort)
        from mcp_core import try_open_browser

        try_open_browser(session.relay_url)

        logger.info("Relay session created: {}", session.relay_url)

        # Start background poll task (non-blocking)
        import asyncio

        asyncio.create_task(_poll_relay_background(relay_base, session, timeout))

        return _setup_url

    except Exception as e:
        logger.debug("Relay setup failed: {}. Server continues in awaiting_setup.", e)
        _state = CredentialState.AWAITING_SETUP
        return None


async def _poll_relay_background(
    relay_base: str, session: object, timeout: float | None
) -> None:
    """Background task that polls relay and applies config when user submits.

    For telegram, this also handles Telethon OTP/2FA auth via relay messaging
    when user-mode credentials are submitted.
    """
    global _state
    try:
        from mcp_core.relay.client import poll_for_result
        from mcp_core.storage.config_file import write_config

        poll_timeout = timeout if timeout is not None else 300.0
        config = await poll_for_result(relay_base, session, timeout_s=poll_timeout)  # ty: ignore[invalid-argument-type]

        # Save config
        write_config(SERVER_NAME, config)

        # Apply to env
        for key, value in config.items():
            if value and key not in os.environ:
                os.environ[key] = value

        # For user mode: run Telethon OTP/2FA auth via relay messaging
        from .relay_setup import _is_user_mode_config

        if _is_user_mode_config(config):
            await _handle_user_mode_auth(relay_base, session, config)
        else:
            # Bot mode: notify completion
            try:
                from mcp_core.relay.client import send_message

                await send_message(
                    relay_base,
                    session.session_id,  # ty: ignore[union-attr]
                    {
                        "type": "complete",
                        "text": "Telegram config saved. Setup complete!",
                    },
                )
            except Exception:
                pass

        _state = CredentialState.CONFIGURED
        logger.info("Relay config applied successfully")

        # Hot-reload: reinitialize backend so tools work without restart
        if _on_configured_callback:
            try:
                await _on_configured_callback()
            except Exception as e:
                logger.warning("Backend reinit after relay failed: {}", e)

        # Release session lock
        from mcp_core import release_session_lock

        await release_session_lock(SERVER_NAME)

    except RuntimeError as e:
        if "RELAY_SKIPPED" in str(e):
            # Telegram has no local fallback, so stay awaiting
            _state = CredentialState.AWAITING_SETUP
            logger.info("Relay skipped by user. Credentials still required.")
        else:
            _state = CredentialState.AWAITING_SETUP
    except Exception:
        _state = CredentialState.AWAITING_SETUP


async def _handle_user_mode_auth(
    relay_base: str, session: object, config: dict[str, str]
) -> None:
    """Handle Telethon OTP/2FA auth after user-mode relay config is submitted."""
    from .config import Settings
    from .relay_setup import _relay_telethon_auth

    settings = Settings.from_relay_config(config)

    from .backends.user_backend import UserBackend

    backend = UserBackend(settings)
    await backend.connect()

    try:
        if not await backend.is_authorized():
            from mcp_core.relay.client import send_message

            await send_message(
                relay_base,
                session.session_id,  # ty: ignore[union-attr]
                {
                    "type": "info",
                    "text": "Credentials saved. Starting Telegram authentication...",
                },
            )

            auth_ok = await _relay_telethon_auth(
                relay_base,
                session.session_id,  # ty: ignore[union-attr]
                backend,
                settings,
            )
            if not auth_ok:
                logger.warning("Relay Telethon auth failed. User can retry later.")
        else:
            from mcp_core.relay.client import send_message

            await send_message(
                relay_base,
                session.session_id,  # ty: ignore[union-attr]
                {
                    "type": "complete",
                    "text": "Existing Telethon session found — already authorized. No OTP needed. You can close this tab.",
                },
            )
    finally:
        await backend.disconnect()


async def save_credentials(config: dict[str, str]) -> dict | None:
    """Save credentials from OAuth form to config.enc and apply to environment.

    Called by the local OAuth AS when the user submits credentials via the
    browser form. Handles both bot mode and user mode.

    Bot mode: saves token, marks configured, returns None (complete).
    User mode: saves phone, returns next_step with OTP instructions.
    OTP verification happens via separate /otp endpoint.

    This function is ``async def`` so we can await Telethon operations
    directly; the OAuth handler awaits the returned coroutine. Calling
    ``loop.run_until_complete()`` from the running Starlette event loop
    raises ``RuntimeError: This event loop is already running``.
    """
    global _state

    from mcp_core.storage.config_file import write_config

    write_config(SERVER_NAME, config)

    for key, value in config.items():
        if value and key not in os.environ:
            os.environ[key] = value

    logger.info("Credentials saved via local OAuth form")

    # Detect mode
    is_user_mode = bool(config.get("TELEGRAM_PHONE")) and not config.get(
        "TELEGRAM_BOT_TOKEN"
    )

    if is_user_mode:
        # User mode: start Telethon auth, send OTP code to Telegram app
        _state = CredentialState.SETUP_IN_PROGRESS
        phone = config.get("TELEGRAM_PHONE", "")
        logger.info("User mode: sending OTP to {}", phone)

        try:
            from .backends.user_backend import UserBackend
            from .config import Settings

            settings = Settings.from_relay_config(config)
            global _step_backend, _step_phone, _step_otp_code
            _step_backend = UserBackend(settings)
            _step_phone = phone
            _step_otp_code = None

            await _connect_and_send_code(_step_backend, phone)
        except Exception as e:
            logger.error("Failed to start Telethon auth: {}", e)
            return {
                "type": "error",
                "text": f"Failed to send OTP: {_sanitize_error(str(e))}",
            }

        return {
            "type": "otp_required",
            "text": "Enter the OTP code sent to your Telegram app",
            "field": "otp_code",
            "input_type": "text",
        }

    # Bot mode: complete immediately
    _state = CredentialState.CONFIGURED

    # Hot-reload backend
    if _on_configured_callback:
        try:
            await _on_configured_callback()
        except Exception as e:
            logger.warning("Backend reinit after save failed: {}", e)

    return None


def set_on_configured(callback: Callable[[], Awaitable[None]]) -> None:
    """Register callback invoked after relay credentials are applied.

    server.py uses this to reinitialize the Telegram backend (hot-reload)
    so tools work immediately without server restart.
    """
    global _on_configured_callback
    _on_configured_callback = callback


def set_state(state: CredentialState) -> None:
    """For testing and setup tool actions."""
    global _state
    _state = state


def reset_state() -> None:
    """Reset to awaiting_setup (used by setup reset action).

    Synchronous: only clears in-memory references. Any Telethon ``_step_backend``
    held is simply dropped -- the garbage collector will close its underlying
    sockets. Attempting ``loop.run_until_complete(backend.disconnect())`` here
    raises ``RuntimeError: loop is already running`` when invoked from an
    async context (e.g. test fixtures or real handlers).
    """
    global _state, _setup_url, _step_backend, _step_phone, _step_otp_code

    _state = CredentialState.AWAITING_SETUP
    _setup_url = None

    # Clean up multi-step OTP flow state (best-effort; let GC handle disconnect)
    _step_backend = None
    _step_phone = ""
    _step_otp_code = None

    try:
        from mcp_core.storage.config_file import delete_config

        delete_config(SERVER_NAME)
    except Exception:
        pass


async def on_step_submitted(step_data: dict[str, str]) -> dict | None:
    """Handle multi-step auth input from /otp endpoint.

    Called by mcp-core when user submits OTP code or 2FA password via the
    credential form's step input. Returns None on success (complete),
    {"type": "password_required", ...} if 2FA is needed, or
    {"type": "error", ...} on failure (allows retry).

    Async: Telethon ``sign_in`` is a coroutine. The OAuth handler in
    mcp-core awaits the returned coroutine, so we can await directly
    instead of smuggling calls onto a running event loop.
    """
    global _step_backend, _step_phone, _step_otp_code

    if _step_backend is None:
        return {"type": "error", "text": "No active authentication session."}

    # OTP code submission
    if "otp_code" in step_data:
        otp_code = step_data["otp_code"].strip()
        _step_otp_code = otp_code

        try:
            await _step_backend.sign_in(_step_phone, otp_code)
            await _finalize_auth()
            return None
        except Exception as e:
            error_msg = str(e)
            if _needs_2fa_password(error_msg):
                return {
                    "type": "password_required",
                    "text": (
                        "Your account has two-factor authentication. "
                        "Enter your 2FA password."
                    ),
                    "field": "password",
                    "input_type": "password",
                }
            # Terminal failure (non-2FA) -- clean up so next attempt starts fresh.
            try:
                await _step_backend.disconnect()
            except Exception:
                pass
            _step_backend = None
            _step_phone = ""
            _step_otp_code = None
            return {
                "type": "error",
                "text": f"Authentication failed: {_sanitize_error(error_msg)}",
            }

    # 2FA password submission
    if "password" in step_data:
        password = step_data["password"]
        if _step_otp_code is None:
            return {
                "type": "error",
                "text": "OTP code missing. Please restart setup.",
            }

        try:
            await _step_backend.sign_in(_step_phone, _step_otp_code, password=password)
            await _finalize_auth()
            return None
        except Exception as e:
            # Terminal failure -- clean up so next attempt starts fresh.
            try:
                await _step_backend.disconnect()
            except Exception:
                pass
            _step_backend = None
            _step_phone = ""
            _step_otp_code = None
            return {
                "type": "error",
                "text": f"2FA failed: {_sanitize_error(str(e))}",
            }

    return {"type": "error", "text": "Unexpected input."}


async def _finalize_auth() -> None:
    """Mark configured and clean up multi-step state (async)."""
    global _state, _step_backend, _step_phone, _step_otp_code

    _state = CredentialState.CONFIGURED

    if _step_backend is not None:
        try:
            await _step_backend.disconnect()
        except Exception:
            pass

    _step_backend = None
    _step_phone = ""
    _step_otp_code = None

    # Hot-reload via existing callback
    if _on_configured_callback:
        try:
            await _on_configured_callback()
        except Exception as e:
            logger.warning("Backend reinit after OTP auth failed: {}", e)
