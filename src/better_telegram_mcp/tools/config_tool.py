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


async def _handle_auth(backend: TelegramBackend, **kwargs: Any) -> str:
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
            "TELEGRAM_PHONE env var is required for auth. Set it in your MCP config."
        )

    password = kwargs.get("password")
    result = await backend.sign_in(phone, code, password=password)

    srv._pending_auth = False
    return ok(
        {
            "message": "Authentication successful.",
            **result,
        }
    )


async def _handle_send_code(backend: TelegramBackend) -> str:
    import better_telegram_mcp.server as srv

    settings = srv.get_settings()
    phone = settings.phone
    if not phone:
        return err(
            "TELEGRAM_PHONE env var is required to send OTP. Set it in your MCP config."
        )

    await backend.send_code(phone)
    srv._pending_auth = True
    return ok(
        {
            "message": f"OTP code sent to {phone}. "
            "Use: config(action='auth', code='YOUR_CODE') to complete."
        }
    )


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
            case "auth":
                return await _handle_auth(backend, **kwargs)
            case "send_code":
                return await _handle_send_code(backend)
            case _:
                return err(
                    f"Unknown action '{action}'. "
                    "Valid: status|set|cache_clear|auth|send_code"
                )
    except Exception as e:
        return safe_error(e)
