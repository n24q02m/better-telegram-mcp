"""Credential resolution helpers for the telegram MCP server.

Public surface used by ``credential_state``:
- ``check_saved_sessions``
- ``_sanitize_error`` / ``_needs_2fa_password``
- Module-level constants (``SERVER_NAME``, ``REQUIRED_FIELDS_*`` ...).

The legacy relay-driven ``_relay_telethon_auth`` and blocking ``ensure_config``
flow was removed -- OTP now arrives via the OAuth credential form and is
verified through the ``/otp`` endpoint (see ``credential_state.save_credentials``
and ``credential_state.on_step_submitted``).
"""

from __future__ import annotations

import re

# Kept at the pre-rename value on purpose: mcp-core keys the legacy shared
# ``config.enc`` entry by this name, and ``run_http_server`` derives the JWT
# signing seed and the stable per-user ``sub`` from ``server_name``. Renaming it
# would orphan saved single-user configs and every per-sub session bucket.
SERVER_NAME = "better-telegram-mcp"
REQUIRED_FIELDS_BOT = ["TELEGRAM_BOT_TOKEN"]
REQUIRED_FIELDS_USER = ["TELEGRAM_PHONE"]
ALL_POSSIBLE_FIELDS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_PHONE",
]

# Telegram bot tokens have the shape "<bot_id>:<35-char secret>" and appear in
# httpx request URLs (https://api.telegram.org/bot<token>/<method>), so they can
# surface in transport-level exception messages. Mask them before logging or
# returning any error string.
_BOT_TOKEN_RE = re.compile(r"\d+:[A-Za-z0-9_-]{35,}")

# Error sanitization patterns shared with credential_state.py.
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


def redact_bot_token(text: str) -> str:
    """Mask any Telegram bot token embedded in ``text``.

    Bot tokens can leak into transport-level error messages because httpx
    includes the request URL (which carries the token) in its exceptions. The
    bot id is preserved for debuggability while the secret is replaced.
    """
    return _BOT_TOKEN_RE.sub(
        lambda m: m.group(0).split(":", 1)[0] + ":<redacted>", text
    )


def _sanitize_error(msg: str) -> str:
    """Simplify internal error messages to user-friendly text."""
    cleaned = redact_bot_token(_CAUSED_BY_RE.sub("", msg).strip())
    for pattern, friendly in _ERROR_SIMPLIFICATIONS:
        if pattern.match(cleaned):
            return friendly
    return cleaned


def _needs_2fa_password(error_msg: str) -> bool:
    """Check if the error indicates 2FA password is required."""
    return any(
        kw in error_msg.lower() for kw in {"password", "2fa", "two-factor", "srp"}
    )


def check_saved_sessions() -> bool:
    """Check for a saved Telethon session from a previous authentication.

    Looks for ``*.session`` files in the default data dir (``~/.telegram/``,
    moved from the legacy ``~/.better-telegram-mcp/`` on first use).

    Returns:
        True if at least one saved session exists, False otherwise.
    """
    from .config import resolve_default_data_dir

    data_dir = resolve_default_data_dir()
    if not data_dir.exists():
        return False
    sessions = list(data_dir.glob("*.session"))
    return len(sessions) > 0
