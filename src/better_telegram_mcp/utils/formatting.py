import json
from typing import Any


def ok(data: Any) -> str:
    """Return a successful response with standardized structure.

    Includes 'status': 'ok' (if not already present in data) and wraps data in 'data' field.
    Spreads data keys to top level for backward compatibility.
    """
    res = {"ok": True, "data": data}
    if isinstance(data, dict):
        res.update(data)
    if "status" not in res:
        res["status"] = "ok"
    return json.dumps(res, ensure_ascii=False, default=str)


def err(message: str) -> str:
    """Return an error response with standardized structure."""
    return json.dumps(
        {"status": "error", "message": message, "error": message},
        ensure_ascii=False,
        default=str,
    )


def safe_error(e: Exception) -> str:
    """Return sanitized error without leaking internal details."""
    from ..backends.base import ModeError
    from ..backends.security import SecurityError

    if isinstance(e, (ModeError, SecurityError, ValueError, FileNotFoundError)):
        return err(str(e))
    return err(f"{type(e).__name__}: Operation failed. Check server logs for details.")
