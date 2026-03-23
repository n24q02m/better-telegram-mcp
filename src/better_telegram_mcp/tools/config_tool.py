from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok, safe_error


async def _handle_status(backend: TelegramBackend, **kwargs: Any) -> str:
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


async def _handle_set(backend: TelegramBackend, **kwargs: Any) -> str:
    from ..server import _runtime_config

    updated: dict[str, int] = {}
    for key in ("message_limit", "timeout"):
        if key in kwargs and kwargs[key] is not None:
            _runtime_config[key] = int(kwargs[key])
            updated[key] = _runtime_config[key]
    if not updated:
        return err("set requires at least one of: message_limit, timeout")
    return ok({"updated": updated, "current": _runtime_config})


async def _handle_cache_clear(backend: TelegramBackend, **kwargs: Any) -> str:
    await backend.clear_cache()
    return ok({"message": "Cache cleared."})


_HANDLERS: dict[str, Callable[..., Awaitable[str]]] = {
    "status": _handle_status,
    "set": _handle_set,
    "cache_clear": _handle_cache_clear,
}


async def handle_config(
    backend: TelegramBackend,
    action: str,
    **kwargs: Any,
) -> str:
    try:
        handler = _HANDLERS.get(action)
        if not handler:
            import difflib

            valid = sorted(_HANDLERS)
            closest = difflib.get_close_matches(action, valid, n=1)
            suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
            return err(
                f"Unknown action '{action}'.{suggestion} Valid: {'|'.join(valid)}"
            )
        return await handler(backend=backend, **kwargs)
    except Exception as e:
        return safe_error(e)
