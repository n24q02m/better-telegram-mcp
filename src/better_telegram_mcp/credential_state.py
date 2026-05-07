"""Non-blocking credential state management for better-telegram-mcp.

State machine: awaiting_setup -> setup_in_progress -> configured
Reset: configured -> awaiting_setup (via setup tool).

Per spec ``2026-05-01-stdio-pure-http-multiuser.md``: stdio mode does not
spawn any in-process credential form — missing creds in stdio mode mean
``main()`` exits 1 with a stderr hint. Browser-based setup (paste form +
OTP/2FA flow) is the responsibility of HTTP mode (``transports/http.py``),
which calls ``mcp_core.transport.run_http_server`` with the same
``save_credentials``/``on_step_submitted`` callbacks defined here.

Hot-reload: after credentials land, the ``on_configured`` callback
(registered by ``server.py``) reinitializes the Telegram backend so tools
work immediately without restart.
"""

from __future__ import annotations

import contextvars
import os
from collections.abc import Awaitable, Callable
from enum import Enum

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


class CredentialState(Enum):
    AWAITING_SETUP = "awaiting_setup"
    SETUP_IN_PROGRESS = "setup_in_progress"
    CONFIGURED = "configured"


# Module-level state
_state = CredentialState.AWAITING_SETUP
_setup_url: str | None = None
_on_configured_callback: Callable[[], Awaitable[None]] | None = None

# Multi-step auth state (single-user HTTP mode)
_step_backend: object | None = None  # UserBackend instance held during OTP flow
_step_phone: str = ""
_step_otp_code: str | None = None  # OTP code remembered for 2FA signin retry

# Per-request JWT subject context for HTTP multi-user mode.
#
# Set by the ``auth_scope`` middleware in ``transports/http.py`` AFTER
# mcp-core verifies the JWT, BEFORE the ASGI tool handler runs, AND set
# again by mcp-core's local OAuth AS during ``/authorize`` POST so
# ``save_credentials`` can route to the right per-sub bucket. ``contextvars``
# is asyncio-task isolated, so concurrent tool calls from different users
# do not bleed credentials across each other.
#
# Stays ``None`` in stdio / single-user HTTP mode — both fall back to the
# shared single-user code path.
_current_sub: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "telegram_current_sub", default=None
)

# Per-sub OTP flow state for multi-user mode (contrast with the single-user
# ``_step_*`` globals above, which are shared across the process). Keyed by
# JWT ``sub``. Each entry is a tuple ``(backend, phone, otp_code | None)``.
# Cleared on success or on next ``setup_reset``.
_per_sub_steps: dict[str, tuple[object, str, str | None]] = {}


async def _connect_and_send_code(backend, phone: str) -> None:
    """Connect Telethon backend and send OTP code to the user's Telegram app."""
    await backend.connect()
    await backend.send_code(phone)


def get_state() -> CredentialState:
    return _state


def get_setup_url() -> str | None:
    return _setup_url


def set_setup_url(url: str | None) -> None:
    """For testing and setup tool actions."""
    global _setup_url
    _setup_url = url


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


async def save_credentials(
    config: dict[str, str], context: dict[str, str]
) -> dict | None:
    """Persist credentials from the local OAuth form and drive Telethon auth.

    Called by ``mcp_core``'s local OAuth AS when the user submits credentials
    via the browser form. Handles both bot mode and user mode.

    Bot mode: validates token (single-user persists to config.enc;
    multi-user registers a per-sub Telethon backend), returns ``None``.
    User mode: triggers Telethon ``send_code``, returns ``otp_required`` so
    the form prompts for the OTP. OTP verification happens via
    ``on_step_submitted`` (bound to ``POST /otp``).

    ``context`` carries the per-authorize ``sub``. In multi-user mode (when
    ``transports/http._start_multi_user_http`` has registered a global
    :class:`TelegramAuthProvider`), credentials are stored per-``sub`` in
    that provider so concurrent users get isolated Telethon sessions. In
    single-user mode the sub is ignored and a single ``config.enc`` on the
    host is reused (existing behaviour, ``feedback_remote_relay_multi_user_enforcement.md``
    refuse-guard ensures this only happens on private networks).
    """
    global _state

    from .auth.telegram_auth_provider import get_global_provider

    provider = get_global_provider()
    sub = (context or {}).get("sub")

    is_user_mode = bool(config.get("TELEGRAM_PHONE")) and not config.get(
        "TELEGRAM_BOT_TOKEN"
    )

    # ----- Multi-user branch: per-sub TelegramAuthProvider -----
    if provider is not None and sub:
        _current_sub.set(sub)

        if is_user_mode:
            _state = CredentialState.SETUP_IN_PROGRESS
            phone = config.get("TELEGRAM_PHONE", "")
            logger.info("Multi-user: starting OTP flow for sub={}", sub[:8])

            try:
                result = await provider.start_user_auth(sub, phone)
                # Provider stores backend internally keyed by sub. Stash the
                # phone so the OTP step can reference it.
                _per_sub_steps[sub] = (None, phone, None)
            except ValueError as e:
                logger.error("Multi-user OTP start failed: {}", e)
                return {
                    "type": "error",
                    "text": f"Failed to send OTP: {_sanitize_error(str(e))}",
                }
            else:
                _ = result  # bearer/phone_code_hash retained inside provider
                return {
                    "type": "otp_required",
                    "text": "Enter the OTP code sent to your Telegram app",
                    "field": "otp_code",
                    "input_type": "text",
                }

        # Bot mode (multi-user): register backend keyed by sub.
        bot_token = config.get("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            return {
                "type": "error",
                "text": "Either bot token or phone number is required.",
            }
        try:
            await provider.register_bot(sub, bot_token)
        except ValueError as e:
            logger.error("Multi-user bot registration failed: {}", e)
            return {
                "type": "error",
                "text": _sanitize_error(str(e)),
            }
        _state = CredentialState.CONFIGURED
        logger.info("Multi-user: bot backend registered for sub={}", sub[:8])
        return None

    # ----- Single-user branch: shared config.enc + global backend -----
    from mcp_core.storage.config_file import write_config

    write_config(SERVER_NAME, config)

    for key, value in config.items():
        if value and key not in os.environ:
            os.environ[key] = value

    logger.info("Credentials saved via local OAuth form")

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

    try:
        from mcp_core.storage.config_file import delete_config

        delete_config(SERVER_NAME)
    except Exception as e:
        logger.warning("Failed to delete config during state reset: {}", e)


async def on_step_submitted(
    step_data: dict[str, str], context: dict[str, str]
) -> dict | None:
    """Handle multi-step auth input from ``/otp`` endpoint.

    Returns ``None`` on success (complete), ``{"type": "password_required", ...}``
    if 2FA is needed, or ``{"type": "error", ...}`` on failure (allows retry).

    ``context`` carries the per-authorize ``sub`` (the same subject passed
    to ``save_credentials``). In multi-user mode we route OTP / 2FA
    submissions through the per-sub :class:`TelegramAuthProvider` so each
    user's Telethon backend stays isolated. Single-user mode keeps the
    legacy module-global ``_step_*`` state.
    """
    from .auth.telegram_auth_provider import get_global_provider

    provider = get_global_provider()
    sub = (context or {}).get("sub")

    # ----- Multi-user branch -----
    if provider is not None and sub:
        if "otp_code" in step_data:
            otp_code = step_data["otp_code"].strip()
            try:
                await provider.complete_user_auth(sub, otp_code)
            except ValueError as e:
                error_msg = str(e)
                if _needs_2fa_password(error_msg):
                    # Stash the otp_code so the password step can re-issue
                    # ``sign_in`` with it (Telethon requires both).
                    if sub in _per_sub_steps:
                        backend, phone, _ = _per_sub_steps[sub]
                        _per_sub_steps[sub] = (backend, phone, otp_code)
                    else:
                        _per_sub_steps[sub] = (None, "", otp_code)
                    return {
                        "type": "password_required",
                        "text": (
                            "Your account has two-factor authentication. "
                            "Enter your 2FA password."
                        ),
                        "field": "password",
                        "input_type": "password",
                    }
                _per_sub_steps.pop(sub, None)
                return {
                    "type": "error",
                    "text": f"Authentication failed: {_sanitize_error(error_msg)}",
                }
            else:
                _per_sub_steps.pop(sub, None)
                global _state
                _state = CredentialState.CONFIGURED
                return None

        if "password" in step_data:
            password = step_data["password"]
            stash = _per_sub_steps.get(sub)
            if stash is None or stash[2] is None:
                return {
                    "type": "error",
                    "text": "OTP code missing. Please restart setup.",
                }
            otp_code = stash[2]
            try:
                await provider.complete_user_auth(sub, otp_code, password=password)
            except ValueError as e:
                _per_sub_steps.pop(sub, None)
                return {
                    "type": "error",
                    "text": f"2FA failed: {_sanitize_error(str(e))}",
                }
            else:
                _per_sub_steps.pop(sub, None)
                _state = CredentialState.CONFIGURED
                return None

        return {"type": "error", "text": "Unexpected input."}

    # ----- Single-user branch -----
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
