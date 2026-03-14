from __future__ import annotations

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok


async def handle_config(
    backend: TelegramBackend,
    action: str,
) -> str:
    try:
        match action:
            case "status":
                connected = await backend.is_connected()
                return ok({
                    "mode": backend.mode,
                    "connected": connected,
                })

            case "set":
                return ok({
                    "message": "Configuration is managed via environment variables. "
                    "See help topic 'config' or README for details."
                })

            case "cache_clear":
                return ok({"message": "Cache cleared (no-op in current version)."})

            case _:
                return err(
                    f"Unknown action '{action}'. "
                    "Valid: status|set|cache_clear"
                )
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
