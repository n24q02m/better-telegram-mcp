from typing import Any


def ok(data: dict[str, Any]) -> dict[str, Any]:
    return data


def err(message: str) -> dict[str, Any]:
    return {"error": message}


def safe_error(e: Exception) -> dict[str, Any]:
    """Return sanitized error without leaking internal details."""
    from ..backends.base import ModeError
    from ..backends.security import SecurityError

    if isinstance(e, (ModeError, SecurityError, ValueError, FileNotFoundError)):
        return err(str(e))
    return err(f"{type(e).__name__}: Operation failed. Check server logs for details.")
