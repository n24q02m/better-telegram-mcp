from __future__ import annotations

from typing import Any

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok, safe_error


async def _handle_status(backend: TelegramBackend) -> str:
    from ..server import _auth_url, _pending_auth, _runtime_config

    connected = await backend.is_connected()
    authorized = await backend.is_authorized()
    result: dict[str, Any] = {
        "mode": backend.mode,
        "connected": connected,
        "authorized": authorized,
        "pending_auth": _pending_auth,
        "config": _runtime_config,
    }
    if _auth_url:
        result["auth_url"] = _auth_url
    return ok(result)


def _handle_set(**kwargs: Any) -> str:
    from ..server import _runtime_config

    updated: dict[str, int] = {}
    for key in ("message_limit", "timeout"):
        if key in kwargs and kwargs[key] is not None:
            _runtime_config[key] = int(kwargs[key])
            updated[key] = _runtime_config[key]
    if not updated:
        return err("set requires at least one of: message_limit, timeout")
    return ok({"updated": updated, "current": _runtime_config})


async def _handle_cache_clear(backend: TelegramBackend) -> str:
    await backend.clear_cache()
    return ok({"message": "Cache cleared."})


async def handle_config(
    backend: TelegramBackend,
    action: str,
    **kwargs: Any,
) -> str:
    try:
        match action:
            case "status":
                return await _handle_status(backend)
            case "set":
                return _handle_set(**kwargs)
            case "cache_clear":
                return await _handle_cache_clear(backend)
            case _:
                return err(f"Unknown action '{action}'. Valid: status|set|cache_clear")
    except Exception as e:
        return safe_error(e)
