import json
from typing import Any


def ok(data: Any) -> str:
    """Return standardized success response with data and optional key spreading."""
    res = {"status": "ok", "ok": True, "data": data}
    if isinstance(data, dict):
        res.update(data)
    return json.dumps(res, ensure_ascii=False, default=str)


def err(message: str) -> str:
    """Return standardized error response."""
    return json.dumps(
        {"status": "error", "message": message, "error": message}, ensure_ascii=False
    )


def safe_error(e: Exception) -> str:
    """Return sanitized error without leaking internal details."""
    from ..backends.base import ModeError
    from ..backends.security import SecurityError

    if isinstance(e, (ModeError, SecurityError, ValueError, FileNotFoundError)):
        return err(str(e))
    return err(f"{type(e).__name__}: Operation failed. Check server logs for details.")
