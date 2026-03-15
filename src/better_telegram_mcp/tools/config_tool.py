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
                from ..server import _pending_auth, _runtime_config

                connected = await backend.is_connected()
                authorized = await backend.is_authorized()
                return ok(
                    {
                        "mode": backend.mode,
                        "connected": connected,
                        "authorized": authorized,
                        "pending_auth": _pending_auth,
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

            case "auth":
                import better_telegram_mcp.server as srv

                if not srv._pending_auth:
                    return ok({"message": "Already authenticated. No action needed."})

                code = kwargs.get("code")
                if not code:
                    return err(
                        "auth requires 'code' parameter. "
                        "Use: config(action='auth', code='YOUR_CODE')"
                    )

                settings = srv.get_settings()
                phone = settings.phone
                if not phone:
                    return err(
                        "TELEGRAM_PHONE env var is required for auth. "
                        "Set it in your MCP config."
                    )

                password = settings.password
                result = await backend.sign_in(phone, code, password=password)

                srv._pending_auth = False
                return ok(
                    {
                        "message": "Authentication successful.",
                        **result,
                    }
                )

            case "send_code":
                import better_telegram_mcp.server as srv

                settings = srv.get_settings()
                phone = settings.phone
                if not phone:
                    return err(
                        "TELEGRAM_PHONE env var is required to send OTP. "
                        "Set it in your MCP config."
                    )

                await backend.send_code(phone)
                srv._pending_auth = True
                return ok(
                    {
                        "message": f"OTP code sent to {phone}. "
                        "Use: config(action='auth', code='YOUR_CODE') to complete."
                    }
                )

            case _:
                return err(
                    f"Unknown action '{action}'. "
                    "Valid: status|set|cache_clear|auth|send_code"
                )
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
