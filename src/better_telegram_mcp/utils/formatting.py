from __future__ import annotations

import json
import re
from typing import Any


def ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def err(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def safe_error(e: Exception) -> str:
    """Return sanitized error without leaking internal details."""
    from ..backends.base import ModeError
    from ..backends.security import SecurityError

    if isinstance(e, (ModeError, SecurityError, ValueError, FileNotFoundError)):
        return err(str(e))
    return err(f"{type(e).__name__}: Operation failed. Check server logs for details.")


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


def sanitize_error(msg: str) -> str:
    """Simplify internal error messages to user-friendly text."""
    cleaned = _CAUSED_BY_RE.sub("", msg).strip()
    for pattern, friendly in _ERROR_SIMPLIFICATIONS:
        if pattern.match(cleaned):
            return friendly
    return cleaned


def mask_phone(phone: str) -> str:
    """Mask phone number for display."""
    if len(phone) > 7:
        return phone[:4] + "***" + phone[-4:]
    if len(phone) > 4:
        return phone[:2] + "***"
    return phone[:2] + "***"
