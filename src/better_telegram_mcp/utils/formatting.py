from __future__ import annotations

import json
from typing import Any


def ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def err(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _mask_phone(phone: str) -> str:
    """Mask phone number for privacy."""
    if not phone:
        return "***"
    length = len(phone)
    if length < 5:
        return "*" * length
    return f"{phone[:2]}{"*" * (length - 4)}{phone[-2:]}"


def safe_error(e: Exception) -> str:
    """Return sanitized error without leaking internal details."""
    from ..backends.base import ModeError
    from ..backends.security import SecurityError

    if isinstance(e, (ModeError, SecurityError, ValueError, FileNotFoundError)):
        return err(str(e))
    return err(f"{type(e).__name__}: Operation failed. Check server logs for details.")
