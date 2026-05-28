from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok, safe_error


class ConfigOptions(BaseModel):
    action: str = Field(description="Action to perform")
    message_limit: int | None = Field(default=None, description="Update message limit")
    timeout: int | None = Field(default=None, description="Update timeout")
    key: str | None = Field(default=None, description="Optional key for some actions")


async def _handle_status(backend: TelegramBackend, options: ConfigOptions) -> str:
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


async def _handle_set(backend: TelegramBackend, options: ConfigOptions) -> str:
    from ..server import _runtime_config

    updated: dict[str, int] = {}
    if options.message_limit is not None:
        _runtime_config["message_limit"] = options.message_limit
        updated["message_limit"] = options.message_limit
    if options.timeout is not None:
        _runtime_config["timeout"] = options.timeout
        updated["timeout"] = options.timeout

    if not updated:
        return err("set requires at least one of: message_limit, timeout")
    return ok({"updated": updated, "current": _runtime_config})


async def _handle_cache_clear(backend: TelegramBackend, options: ConfigOptions) -> str:
    await backend.clear_cache()
    return ok({"message": "Cache cleared."})


_HANDLERS: dict[str, Callable[[TelegramBackend, ConfigOptions], Awaitable[str]]] = {
    "status": _handle_status,
    "set": _handle_set,
    "cache_clear": _handle_cache_clear,
}


async def handle_config(
    backend: TelegramBackend,
    options: ConfigOptions,
) -> str:
    try:
        handler = _HANDLERS.get(options.action)
        if not handler:
            import difflib

            valid = sorted(_HANDLERS)
            closest = difflib.get_close_matches(options.action, valid, n=1)
            suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
            return err(
                f"Unknown action '{options.action}'.{suggestion} Valid: {'|'.join(valid)}"
            )
        return await handler(backend, options)
    except Exception as e:
        return safe_error(e)
