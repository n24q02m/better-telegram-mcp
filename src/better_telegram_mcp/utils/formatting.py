from __future__ import annotations

import json
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


def _mask_phone(phone: str) -> str:
    """Mask a phone number for display."""
    if len(phone) > 7:
        return phone[:4] + "***" + phone[-4:]
    return phone[:2] + "***"
