"""Credential resolution helpers for better-telegram-mcp.

Public surface used by ``credential_state``:
- ``check_saved_sessions`` / ``_is_user_mode_config``
- ``_sanitize_error`` / ``_needs_2fa_password``
- Module-level constants (``SERVER_NAME``, ``REQUIRED_FIELDS_*`` ...).

The legacy relay-driven ``_relay_telethon_auth`` and blocking ``ensure_config``
flow was removed -- OTP now arrives via the OAuth credential form and is
verified through the ``/otp`` endpoint (see ``credential_state.save_credentials``
and ``credential_state.on_step_submitted``).
"""

from __future__ import annotations

import re
from pathlib import Path

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
