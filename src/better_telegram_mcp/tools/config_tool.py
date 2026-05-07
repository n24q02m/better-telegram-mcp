from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok, safe_error


async def _handle_status(backend: TelegramBackend | None, **kwargs: Any) -> str:
    from ..server import _pending_auth, _runtime_config, _unconfigured

    if backend is None or _unconfigured:
        return ok(
            {
                "mode": None,
                "connected": False,
                "authorized": False,
                "configured": False,
                "config": _runtime_config,
                "setup": {
                    "bot_mode": "Set TELEGRAM_BOT_TOKEN (get from @BotFather)",
                    "user_mode": (
                        "Set TELEGRAM_PHONE"
                        " (API credentials have built-in defaults)"
                    ),
                },
                "hint": "Use action='setup_start' to configure via browser relay.",
            }
        )

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


async def _handle_set(backend: TelegramBackend | None, **kwargs: Any) -> str:
    from ..server import (
        _not_ready_response,
        _pending_auth,
        _runtime_config,
        _unconfigured,
    )

    if backend is None or _unconfigured or _pending_auth:
        return _not_ready_response()

    updated: dict[str, int] = {}
    for key in ("message_limit", "timeout"):
        if key in kwargs and kwargs[key] is not None:
            _runtime_config[key] = int(kwargs[key])
            updated[key] = _runtime_config[key]
    if not updated:
        return err("set requires at least one of: message_limit, timeout")
    return ok({"updated": updated, "current": _runtime_config})


async def _handle_cache_clear(backend: TelegramBackend | None, **kwargs: Any) -> str:
    from ..server import _not_ready_response, _pending_auth, _unconfigured

    if backend is None or _unconfigured or _pending_auth:
        return _not_ready_response()

    await backend.clear_cache()
    return ok({"message": "Cache cleared."})


async def _handle_setup_status(backend: TelegramBackend | None, **kwargs: Any) -> str:
    import os

    from ..credential_state import get_setup_url, get_state
    from ..server import _pending_auth, _unconfigured

    state = get_state()
    return ok(
        {
            "state": state.value,
            "setup_url": get_setup_url(),
            "configured": not _unconfigured,
            "pending_auth": _pending_auth,
            "env_keys": [
                k
                for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_PHONE")
                if os.environ.get(k)
            ],
        }
    )


async def _handle_setup_start(backend: TelegramBackend | None, **kwargs: Any) -> str:
    from ..credential_state import CredentialState, get_state

    key = kwargs.get("key")
    if get_state() == CredentialState.CONFIGURED and not (
        key and key.lower() == "force"
    ):
        return ok(
            {
                "status": "already_configured",
                "message": "Already configured. Use key='force' to reconfigure.",
            }
        )
    # Per spec 2026-05-01-stdio-pure-http-multiuser.md: stdio mode does
    # not spawn an in-process credential form. Browser-based setup is
    # the responsibility of HTTP mode; this branch tells the user how
    # to switch.
    return ok(
        {
            "status": "stdio_unsupported",
            "message": (
                "Browser-based setup is HTTP-mode only. "
                "For stdio mode, set TELEGRAM_BOT_TOKEN in your "
                "plugin/server config (get from @BotFather). "
                "For user-mode auth (phone+OTP), switch to HTTP mode "
                "(see docs/setup-manual.md)."
            ),
        }
    )


async def _handle_setup_reset(backend: TelegramBackend | None, **kwargs: Any) -> str:
    from ..credential_state import reset_state

    reset_state()
    return ok(
        {
            "status": "ok",
            "message": "Credentials cleared. Use setup_start to reconfigure.",
        }
    )


async def _handle_setup_complete(backend: TelegramBackend | None, **kwargs: Any) -> str:
    from ..credential_state import (
        get_state,
        resolve_credential_state,
    )

    resolve_credential_state()
    state = get_state()
    return ok(
        {
            "status": "ok",
            "state": state.value,
            "message": "Credential state refreshed.",
        }
    )


_HANDLERS: dict[str, Callable[..., Awaitable[str]]] = {
    "status": _handle_status,
    "set": _handle_set,
    "cache_clear": _handle_cache_clear,
    "setup_status": _handle_setup_status,
    "setup_start": _handle_setup_start,
    "setup_reset": _handle_setup_reset,
    "setup_complete": _handle_setup_complete,
}


async def handle_config(
    backend: TelegramBackend | None,
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
