"""Non-blocking credential state management for better-telegram-mcp.

State machine: awaiting_setup -> setup_in_progress -> configured
Reset: configured -> awaiting_setup (via setup tool).

When no credentials are present, ``trigger_relay_setup`` spawns a LOCAL HTTP
credential form on ``http://127.0.0.1:<random>`` via
``mcp_core.start_local_server_background`` with the telegram relay schema.
The user submits a phone number (user mode) or bot token (bot mode) into
that local form; ``save_credentials`` persists to ``config.enc``, and — for
user mode — returns an ``otp_required`` prompt so the form asks for the
OTP. ``on_step_submitted`` then drives Telethon sign-in + optional 2FA
entirely against the local form's ``/otp`` endpoint.

This fallback is LOCAL-ONLY. We never hit the remote relay URL here — that
is reserved for explicit ``MCP_MODE`` HTTP deployments. See
``~/.claude/skills/mcp-dev/references/mode-matrix.md`` section ``stdio proxy``
for the canonical rule.

Hot-reload: after credentials land, the ``on_configured`` callback
(registered by ``server.py``) reinitializes the Telegram backend so tools
work immediately without restart.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from loguru import logger

from .relay_setup import (
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

# Grace window so the browser renders "Setup complete!" before the local spawn closes.
_SPAWN_CLEANUP_S = 5.0


class CredentialState(Enum):
    AWAITING_SETUP = "awaiting_setup"
    SETUP_IN_PROGRESS = "setup_in_progress"
    CONFIGURED = "configured"


# Module-level state
_state = CredentialState.AWAITING_SETUP
_setup_url: str | None = None
_on_configured_callback: Callable[[], Awaitable[None]] | None = None
_active_handle: Any | None = None  # LocalServerHandle

# Multi-step auth state (single-user local mode)
_step_backend: object | None = None  # UserBackend instance held during OTP flow
_step_phone: str = ""
_step_otp_code: str | None = None  # OTP code remembered for 2FA signin retry


async def _connect_and_send_code(backend, phone: str) -> None:
    """Connect Telethon backend and send OTP code to the user's Telegram app."""
    await backend.connect()
    await backend.send_code(phone)


def get_state() -> CredentialState:
    return _state


def get_setup_url() -> str | None:
    return _setup_url


def resolve_credential_state() -> CredentialState:
    """Fast, synchronous credential check. Called during lifespan startup.

    Checks (in order):
    1. ENV VARS -- bot_token or TELEGRAM_PHONE present -> CONFIGURED
    2. CONFIG FILE -- saved config has credential keys -> CONFIGURED
    3. SAVED SESSIONS -- Telethon session files exist -> AWAITING_SETUP
       (session files exist but user still needs phone)
    4. NOTHING -- AWAITING_SETUP
    """
    global _state

    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.info("Bot token found in environment")
        _state = CredentialState.CONFIGURED
        return _state

    if os.environ.get("TELEGRAM_PHONE"):
        logger.info("User mode credentials found in environment")
        _state = CredentialState.CONFIGURED
        return _state

    try:
        from mcp_core.storage.config_file import read_config

        saved = read_config(SERVER_NAME)
        if saved:
            has_bot = bool(saved.get("TELEGRAM_BOT_TOKEN"))
            has_user = bool(saved.get("TELEGRAM_PHONE"))
            if has_bot or has_user:
                for key, value in saved.items():
                    if value and key not in os.environ:
                        os.environ[key] = value
                logger.info("Config loaded from encrypted file")
                _state = CredentialState.CONFIGURED
                return _state
    except Exception as e:
        logger.debug("Failed to read config during state resolution: {}", e)

    if check_saved_sessions():
        logger.info(
            "Found saved Telethon session files. "
            "Set TELEGRAM_PHONE to reuse them "
            "(API credentials have built-in defaults)."
        )
        _state = CredentialState.AWAITING_SETUP
        return _state

    logger.info("No credentials found -- server starting in awaiting_setup mode")
    _state = CredentialState.AWAITING_SETUP
    return _state


async def _close_active_handle() -> None:
    """Best-effort close of the module-level local credential-form handle."""
    global _active_handle

    handle = _active_handle
    _active_handle = None
    if handle is None:
        return
    try:
        await handle.close()
    except Exception as e:
        logger.debug("Best-effort close of credential-form handle failed: {}", e)


def _schedule_spawn_cleanup(grace_s: float = _SPAWN_CLEANUP_S) -> None:
    """Schedule detached cleanup of the local credential-form spawn.

    The grace window lets the browser render the completion UI before the
    server goes away.
    """
    global _active_handle
    if _active_handle is None:
        return

    async def _delayed_close() -> None:
        try:
            await asyncio.sleep(grace_s)
            await _close_active_handle()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug("Delayed spawn cleanup failed: {}", e)

    task = asyncio.create_task(_delayed_close())
    task.add_done_callback(lambda _t: None)


async def trigger_relay_setup(
    *, force: bool = False, timeout: float | None = None
) -> str | None:
    """Spawn a local credential form (stdio fallback) and return its URL.

    The spawn is LOCAL ONLY — ``mcp_core.start_local_server_background``
    binds ``127.0.0.1:<random>`` and renders the telegram relay schema in a
    browser form. The returned URL is handed back to the tool response so
    the user can open it.

    Args:
        force: Re-spawn even when not in ``AWAITING_SETUP``.
        timeout: Unused (kept for backward compatibility with the old remote
            relay poll timeout argument).

    Returns:
        The local setup URL, or ``None`` if the spawn could not be started.
    """
    global _state, _setup_url, _active_handle

    if not force and _state not in (CredentialState.AWAITING_SETUP,):
        return _setup_url

    # If we already have a live spawn, reuse it instead of binding a new port.
    if _active_handle is not None and _setup_url:
        _state = CredentialState.SETUP_IN_PROGRESS
        return _setup_url

    _state = CredentialState.SETUP_IN_PROGRESS

    try:
        from fastmcp import FastMCP
        from mcp_core import start_local_server_background, try_open_browser

        from .credential_form import render_telegram_credential_form
        from .relay_schema import RELAY_SCHEMA

        stub_mcp = FastMCP(f"{SERVER_NAME}-setup")

        handle = await start_local_server_background(
            stub_mcp,
            server_name=SERVER_NAME,
            relay_schema=RELAY_SCHEMA,
            port=0,
            host="127.0.0.1",
            on_credentials_saved=save_credentials,
            on_step_submitted=on_step_submitted,
            custom_credential_form_html=render_telegram_credential_form,
        )

        _active_handle = handle
        _setup_url = f"http://{handle.host}:{handle.port}/"

        try_open_browser(_setup_url)

        logger.info("Local credential form ready at {}", _setup_url)
        return _setup_url

    except Exception as e:
        logger.debug("Relay setup failed: {}. Server continues in awaiting_setup.", e)
        _state = CredentialState.AWAITING_SETUP
        await _close_active_handle()
        _setup_url = None
        return None


async def save_credentials(
    config: dict[str, str], _context: dict[str, str]
) -> dict | None:
    """Persist credentials from the local OAuth form and drive Telethon auth.

    Called by ``mcp_core``'s local OAuth AS when the user submits credentials
    via the browser form. Handles both bot mode and user mode.

    Bot mode: saves token, marks configured, returns ``None`` (complete).
    User mode: saves phone, triggers Telethon send_code, returns
    ``otp_required`` so the form prompts for the OTP. OTP verification
    happens via ``on_step_submitted`` (bound to ``POST /otp``).

    ``_context`` carries the per-authorize ``sub``. The current public-URL
    deployment (``better-telegram-mcp.n24q02m.com``) is intended as a
    single-user self-host target — the Telethon session is a physical device
    login bound to one phone number, so splitting by JWT sub does not yield a
    usable multi-user experience. Consumers who want public multi-tenant
    should run one container per user (each with its own ``config.enc`` +
    session file) behind an auth proxy rather than sharing the session file.
    The sub is still accepted so the callback signature matches the mcp-core
    contract introduced for remote-relay isolation (email etc.).
    """
    global _state

    from mcp_core.storage.config_file import write_config

    write_config(SERVER_NAME, config)

    for key, value in config.items():
        if value and key not in os.environ:
            os.environ[key] = value

    logger.info("Credentials saved via local OAuth form")

    is_user_mode = bool(config.get("TELEGRAM_PHONE")) and not config.get(
        "TELEGRAM_BOT_TOKEN"
    )

    if is_user_mode:
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

    if _on_configured_callback:
        try:
            await _on_configured_callback()
        except Exception as e:
            logger.warning("Backend reinit after save failed: {}", e)

    _schedule_spawn_cleanup()
    return None


def set_on_configured(callback: Callable[[], Awaitable[None]]) -> None:
    """Register callback invoked after relay credentials are applied.

    ``server.py`` uses this to reinitialize the Telegram backend (hot-reload)
    so tools work immediately without server restart.
    """
    global _on_configured_callback
    _on_configured_callback = callback


def set_state(state: CredentialState) -> None:
    """For testing and setup tool actions."""
    global _state
    _state = state


def reset_state() -> None:
    """Reset to ``AWAITING_SETUP`` (used by setup reset action)."""
    global _state, _setup_url, _step_backend, _step_phone, _step_otp_code

    _state = CredentialState.AWAITING_SETUP
    _setup_url = None

    _step_backend = None
    _step_phone = ""
    _step_otp_code = None

    # Close any active local credential-form spawn. Fire-and-forget task so
    # callers don't need to be async.
    if _active_handle is not None:
        try:
            task = asyncio.create_task(_close_active_handle())
            task.add_done_callback(lambda _t: None)
        except RuntimeError:
            # No running loop; state is cleared regardless.
            pass

    try:
        from mcp_core.storage.config_file import delete_config

        delete_config(SERVER_NAME)
    except Exception as e:
        logger.warning("Failed to delete config during state reset: {}", e)


async def on_step_submitted(
    step_data: dict[str, str], _context: dict[str, str]
) -> dict | None:
    """Handle multi-step auth input from ``/otp`` endpoint.

    Returns ``None`` on success (complete), ``{"type": "password_required", ...}``
    if 2FA is needed, or ``{"type": "error", ...}`` on failure (allows retry).

    ``_context`` carries the per-authorize ``sub`` (the same subject passed
    to ``save_credentials``). The deployed single-user fallback ignores it;
    multi-user migration (future) will key the Telethon client + session file
    by this sub so concurrent remote-relay users don't share 2FA state.
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
            try:
                await _step_backend.disconnect()
            except Exception as disconnect_err:
                logger.debug("Best-effort disconnect failed: {}", disconnect_err)
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
            error_msg = str(e)
            try:
                await _step_backend.disconnect()
            except Exception as disconnect_err:
                logger.debug("Best-effort disconnect failed: {}", disconnect_err)
            _step_backend = None
            _step_phone = ""
            _step_otp_code = None
            return {
                "type": "error",
                "text": f"2FA failed: {_sanitize_error(error_msg)}",
            }

    return {"type": "error", "text": "Unexpected input."}


async def _finalize_auth() -> None:
    """Mark configured and clean up multi-step state (async)."""
    global _state, _step_backend, _step_phone, _step_otp_code

    _state = CredentialState.CONFIGURED

    if _step_backend is not None:
        try:
            await _step_backend.disconnect()
        except Exception as e:
            logger.debug("Best-effort disconnect failed: {}", e)

    _step_backend = None
    _step_phone = ""
    _step_otp_code = None

    if _on_configured_callback:
        try:
            await _on_configured_callback()
        except Exception as e:
            logger.warning("Backend reinit after OTP auth failed: {}", e)

    _schedule_spawn_cleanup()
