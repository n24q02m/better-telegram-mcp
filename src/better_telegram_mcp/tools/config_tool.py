from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from ..backends.base import TelegramBackend
from ..utils.formatting import err, ok, safe_error


class ConfigOptions(BaseModel):
    """Arguments for the config tool."""

    action: str
    message_limit: int | None = Field(default=None)
    timeout: int | None = Field(default=None)
    key: str | None = Field(default=None)


async def _handle_status(
    backend: TelegramBackend | None, options: ConfigOptions
) -> str:
    from ..server import _pending_auth, _runtime_config, _unconfigured

    if _unconfigured or backend is None:
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
                        "Set TELEGRAM_PHONE (API credentials have built-in defaults)"
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


async def _handle_set(backend: TelegramBackend | None, options: ConfigOptions) -> str:
    from ..server import _runtime_config

    updated: dict[str, int] = {}
    if options.message_limit is not None:
        _runtime_config["message_limit"] = int(options.message_limit)
        updated["message_limit"] = _runtime_config["message_limit"]
    if options.timeout is not None:
        _runtime_config["timeout"] = int(options.timeout)
        updated["timeout"] = _runtime_config["timeout"]

    if not updated:
        return err("set requires at least one of: message_limit, timeout")
    return ok({"updated": updated, "current": _runtime_config})


async def _handle_cache_clear(
    backend: TelegramBackend | None, options: ConfigOptions
) -> str:
    if backend is None:
        return err("Backend not initialized.")
    await backend.clear_cache()
    return ok({"message": "Cache cleared."})


async def _handle_setup_status(
    backend: TelegramBackend | None, options: ConfigOptions
) -> str:
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
                k for k in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_PHONE"} if os.environ.get(k)
            ],
        }
    )


async def _handle_setup_start(
    backend: TelegramBackend | None, options: ConfigOptions
) -> str:
    from ..credential_state import CredentialState, get_state

    if get_state() == CredentialState.CONFIGURED and not (
        options.key and options.key.lower() == "force"
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
                "(see https://mcp.n24q02m.com/servers/better-telegram-mcp/setup/)."
            ),
        }
    )


async def _handle_setup_reset(
    backend: TelegramBackend | None, options: ConfigOptions
) -> str:
    from ..credential_state import reset_state

    reset_state()
    return ok(
        {
            "status": "ok",
            "message": "Credentials cleared. Use setup_start to reconfigure.",
        }
    )


async def _handle_setup_complete(
    backend: TelegramBackend | None, options: ConfigOptions
) -> str:
    from ..credential_state import get_state, resolve_credential_state

    resolve_credential_state()
    state = get_state()
    return ok(
        {
            "status": "ok",
            "state": state.value,
            "message": "Credential state refreshed.",
        }
    )


_HANDLERS: dict[
    str, Callable[[TelegramBackend | None, ConfigOptions], Awaitable[str]]
] = {
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
    action: str | ConfigOptions,
    **kwargs: Any,
) -> str:
    if isinstance(action, str):
        options = ConfigOptions(action=action, **kwargs)
    else:
        options = action

    try:
        from ..server import _not_ready_response, _unconfigured

        handler = _HANDLERS.get(options.action)
        if not handler:
            import difflib

            valid = sorted(_HANDLERS)
            closest = difflib.get_close_matches(options.action, valid, n=1)
            suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
            return err(
                f"Unknown action '{options.action}'.{suggestion} Valid: {'|'.join(valid)}"
            )

        # Pre-check for unconfigured state if not a setup action or status
        if (
            _unconfigured
            and options.action not in {"status"}
            and not options.action.startswith("setup_")
        ):
            return _not_ready_response()

        return await handler(backend, options)
    except Exception as e:
        return safe_error(e)
