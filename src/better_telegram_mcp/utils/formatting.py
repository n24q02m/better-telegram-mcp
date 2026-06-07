import json
from typing import Any


def ok(data: Any) -> str:
    """Return success response as JSON string."""
    response = {"status": "ok", "ok": True, "data": data}
    if isinstance(data, dict):
        response.update(data)
    return json.dumps(response, ensure_ascii=False, default=str)


def err(message: str) -> str:
    """Return error response as JSON string."""
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
