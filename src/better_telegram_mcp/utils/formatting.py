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


def empty_to_none(v: str | None) -> str | None:
    """Treat empty or whitespace-only string as None (plugin.json sets env vars to '' by default)."""
    if not v or not v.strip():
        return None
    return v
