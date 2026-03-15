from __future__ import annotations

from typing import Any

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok


async def handle_config(
    backend: TelegramBackend,
    action: str,
    **kwargs: Any,
) -> str:
    try:
        match action:
            case "status":
                from ..server import _runtime_config

                connected = await backend.is_connected()
                return ok(
                    {
                        "mode": backend.mode,
                        "connected": connected,
                        "config": _runtime_config,
                    }
                )

            case "set":
                from ..server import _runtime_config

                updated: dict[str, int] = {}
                for key in ("message_limit", "timeout"):
                    if key in kwargs and kwargs[key] is not None:
                        _runtime_config[key] = int(kwargs[key])
                        updated[key] = _runtime_config[key]
                if not updated:
                    return err("set requires at least one of: message_limit, timeout")
                return ok({"updated": updated, "current": _runtime_config})

            case "cache_clear":
                await backend.clear_cache()
                return ok({"message": "Cache cleared."})

            case _:
                return err(f"Unknown action '{action}'. Valid: status|set|cache_clear")
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
