from collections.abc import Awaitable, Callable
from typing import Any

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok, safe_error


async def _handle_status(backend: TelegramBackend, **kwargs: Any) -> dict[str, Any]:
    from ..server import _pending_auth, _runtime_config

    connected = await backend.is_connected()
    authorized = await backend.is_authorized()
    result: dict[str, Any] = {
        "mode": backend.mode,
        "connected": connected,
        "authorized": authorized,
        "pending_auth": _pending_auth,
        "config": _runtime_config,
    }
    return ok(result)


# Runtime limits settable via ``config(action="set")`` -- both as typed params
# (message_limit=, timeout=) and generically (key=, value=) for parity with the
# other servers' ``set`` action.
_SETTABLE_KEYS = ("message_limit", "timeout")


async def _handle_set(backend: TelegramBackend, **kwargs: Any) -> dict[str, Any]:
    from ..server import _runtime_config

    updated: dict[str, int] = {}

    # Generic key/value form (parity with the other servers' ``set`` action).
    key = kwargs.get("key")
    value = kwargs.get("value")
    if key is not None or value is not None:
        if not key or value is None:
            return err("set (generic form) requires both key and value")
        if key not in _SETTABLE_KEYS:
            import difflib

            closest = difflib.get_close_matches(key, list(_SETTABLE_KEYS), n=1)
            suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
            return err(
                f"Invalid key: {key}.{suggestion} Valid: {'|'.join(_SETTABLE_KEYS)}"
            )
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            return err(f"'{key}' must be an integer, got: {value!r}")
        _runtime_config[key] = coerced
        updated[key] = coerced

    # Typed sugar params (message_limit=, timeout=).
    for typed_key in _SETTABLE_KEYS:
        if kwargs.get(typed_key) is not None:
            _runtime_config[typed_key] = int(kwargs[typed_key])
            updated[typed_key] = _runtime_config[typed_key]

    if not updated:
        return err("set requires at least one of: key+value, message_limit, timeout")
    return ok({"updated": updated, "current": _runtime_config})


async def _handle_cache_clear(
    backend: TelegramBackend, **kwargs: Any
) -> dict[str, Any]:
    await backend.clear_cache()
    return ok({"message": "Cache cleared."})


_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "status": _handle_status,
    "set": _handle_set,
    "cache_clear": _handle_cache_clear,
}


async def handle_config(
    backend: TelegramBackend,
    action: str,
    **kwargs: Any,
) -> dict[str, Any]:
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
