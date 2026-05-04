"""HTTP transport mode for better-telegram-mcp.

Two outcomes (both via mcp-core ``run_http_server``):

- **Multi-user remote** when ``DCR_SERVER_SECRET`` + ``PUBLIC_URL`` + a
  Telegram ``api_id``/``api_hash`` pair are present. mcp-core's local OAuth
  AS issues a per-authorize ``sub`` UUID, and the ``auth_scope`` middleware
  pins that sub into a contextvar so per-tool-call handlers resolve the
  right per-user Telethon backend. Credentials land in
  ``TelegramAuthProvider`` keyed by sub, NOT by raw bearer (per-JWT-sub
  isolation, ``feedback_remote_relay_multi_user_enforcement.md``).

- **Single-user paste-form fallback** for self-host / localhost. Same
  browser paste-form flow as the other plugins (notion, email, wet, mnemo,
  crg) — ``run_http_server`` renders the custom Telegram credential form,
  OTP/2FA flow runs against ``/otp``, and the global single backend in
  ``server.py`` is hot-reloaded once credentials land.

The ``api_id``/``api_hash`` pair has built-in defaults in ``config.py``
(public Telegram app registration) so a deployed container only needs
``DCR_SERVER_SECRET`` + ``PUBLIC_URL`` set to flip on multi-user.

Per spec ``2026-05-01-stdio-pure-http-multiuser.md``: there is no
``MCP_MODE`` env var, no remote-relay client, no daemon-bridge. Stdio mode
is handled in ``server.main()`` and never reaches this module.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any

from loguru import logger

from ..config import Settings
from ..relay_schema import RELAY_SCHEMA

# ContextVar for per-user backend injection in multi-user HTTP mode.
#
# In single-user mode this stays unset; ``server.get_backend()`` falls
# back to the global ``_backend``.
#
# In multi-user mode the ``auth_scope`` middleware (``_per_request_sub_scope``
# below) sets it from ``TelegramAuthProvider.resolve_backend(sub)`` AFTER
# JWT verification, BEFORE the inner ASGI MCP handler runs. The ``next_()``
# coroutine dispatches the actual MCP request inside the same asyncio task,
# so the contextvar set here is visible to tool handlers and is reset on
# the way out so a stale backend does not leak between requests.
_current_backend: ContextVar = ContextVar("current_backend")


def get_current_backend():
    """Get the per-user backend from context (HTTP mode).

    Returns None if not in HTTP mode or no backend set.
    """
    return _current_backend.get(None)


def _is_multi_user_mode(settings: Settings | None = None) -> bool:
    """Check if multi-user HTTP mode is configured.

    Multi-user requires: ``DCR_SERVER_SECRET`` (OAuth shared secret) +
    ``PUBLIC_URL`` (deployed hostname) + a Telegram ``api_id`` / ``api_hash``
    pair. The api_id/api_hash pair is satisfied either by the corresponding
    env vars OR by the built-in Settings defaults (the code ships a public
    app registration — see ``config.py``), so a deployed container only
    needs to set the two "secret" variables to flip on multi-user mode.
    """
    has_dcr = bool(os.environ.get("DCR_SERVER_SECRET"))
    has_public_url = bool(os.environ.get("PUBLIC_URL"))
    if settings is None:
        settings = Settings()
    has_api = bool(settings.api_id) and bool(settings.api_hash)
    return has_dcr and has_public_url and has_api


def start_http(settings: Settings) -> None:
    """Start MCP server in HTTP mode.

    Three outcomes:
    - Full multi-user OAuth 2.1 when ``DCR_SERVER_SECRET`` + ``PUBLIC_URL``
      are set and a ``api_id``/``api_hash`` pair is available (via env var
      or the built-in Settings defaults). Per-JWT-sub Telethon clients,
      isolated credentials, the intended public-deploy mode.
    - Single-user relay fallback when ``PUBLIC_URL`` is absent — that's
      self-host / localhost ``uvx`` usage and a single shared config is
      correct there.
    - ``RuntimeError`` when ``PUBLIC_URL`` is set but ``DCR_SERVER_SECRET``
      or the api_id/api_hash pair is missing. Without all three, the
      fallback would serve a shared ``default.session`` + ``TELEGRAM_PHONE``
      across every visitor, which leaks credentials (the 2026-04-21
      incident). Refuse to start rather than silently ship that behaviour.
      Override with ``TELEGRAM_ACCEPT_SHARED_SINGLE_USER=1`` iff you really
      do own every request (e.g. a private CF Tunnel behind basic auth).
    """
    if _is_multi_user_mode(settings):
        _start_multi_user_http(settings)
        return

    public_url = os.environ.get("PUBLIC_URL")
    override = os.environ.get("TELEGRAM_ACCEPT_SHARED_SINGLE_USER") == "1"
    if public_url and not override:
        missing = []
        if not os.environ.get("DCR_SERVER_SECRET"):
            missing.append("DCR_SERVER_SECRET")
        if not (settings.api_id and settings.api_hash):
            missing.append("TELEGRAM_API_ID and TELEGRAM_API_HASH")
        msg = (
            "Refusing to start: PUBLIC_URL is set (public deploy detected) "
            "but multi-user mode requires "
            f"{', '.join(missing)} to be set as well. Without them the server "
            "falls back to a SHARED default.session + TELEGRAM_PHONE across "
            "every visitor, which leaks credentials. Either provide the "
            "missing values to enable per-user OAuth 2.1, or set "
            "TELEGRAM_ACCEPT_SHARED_SINGLE_USER=1 to explicitly opt in to "
            "single-user behaviour (only safe on private networks)."
        )
        raise RuntimeError(msg)

    _start_single_user_http(settings)


def _start_single_user_http(settings: Settings) -> None:
    """Single-user HTTP mode via mcp-core HTTP server + browser paste form.

    Same browser paste-form flow as the other MCP servers (notion, email,
    wet, mnemo, crg). Uses ``run_http_server`` from mcp-core so /authorize
    renders the custom telegram credential form and OTP/2FA steps are
    handled via ``/otp`` against the local OAuth AS.
    """
    import asyncio

    from mcp_core.transport.local_server import run_http_server

    from ..credential_form import render_telegram_credential_form
    from ..credential_state import on_step_submitted, save_credentials
    from ..server import mcp

    port = int(os.environ.get("PORT", "0"))
    host = os.environ.get("HOST")

    asyncio.run(
        run_http_server(
            mcp,
            server_name="better-telegram-mcp",
            relay_schema=RELAY_SCHEMA,
            port=port,
            host=host,
            on_credentials_saved=save_credentials,
            on_step_submitted=on_step_submitted,
            custom_credential_form_html=render_telegram_credential_form,
        )
    )


async def _per_request_sub_scope(
    claims: dict[str, Any],
    next_: Any,
) -> None:
    """``auth_scope`` middleware: pin per-request JWT sub + per-user backend.

    Invoked by mcp-core's ``BearerMCPApp`` AFTER JWT verification, BEFORE the
    inner ASGI MCP handler runs. The ``next_()`` coroutine dispatches the
    actual MCP request inside the same asyncio task, so contextvars set here
    are visible to tool handlers and are reset on the way out so stale state
    does not leak between requests (a critical guarantee for multi-user
    safety).

    We pin two things per request:

    1. ``credential_state._current_sub`` — the JWT ``sub`` so handlers
       like ``save_credentials`` / ``on_step_submitted`` (called via
       hot-reload paths or future per-sub config writes) know which user
       the request is for.
    2. ``transports.http._current_backend`` — the resolved per-user
       Telethon backend pulled from ``TelegramAuthProvider`` keyed by
       sub. ``server.get_backend()`` reads this contextvar so tools
       dispatched in this request execute against the right user.

    If the user has not completed setup yet the backend lookup returns
    ``None`` and we leave ``_current_backend`` unset — tool handlers will
    raise the standard ``Backend not initialized`` error which surfaces as
    a "not authenticated" message via ``_not_ready_response()``.
    """
    from ..auth.telegram_auth_provider import get_global_provider
    from ..credential_state import _current_sub

    sub = claims.get("sub")
    sub_token = _current_sub.set(sub)
    backend_token = None
    if sub:
        provider = get_global_provider()
        if provider is not None:
            backend = provider.resolve_backend(sub)
            keys_preview = list(provider.active_clients.keys())
            keys_short = [
                k[:12] + "..." if len(k) > 12 else k for k in keys_preview[:5]
            ]
            logger.info(
                "auth_scope: sub={} found_backend={} active_keys_count={} keys={}",
                (sub or "")[:12] + "...",
                type(backend).__name__ if backend else "None",
                len(provider.active_clients),
                keys_short,
            )
            if backend is not None:
                backend_token = _current_backend.set(backend)
        else:
            logger.warning(
                "auth_scope: get_global_provider() returned None (sub={})",
                (sub or "")[:12],
            )
    else:
        logger.warning(
            "auth_scope: claims has no 'sub' field, claims_keys={}", list(claims.keys())
        )

    try:
        await next_()
    finally:
        _current_sub.reset(sub_token)
        if backend_token is not None:
            _current_backend.reset(backend_token)


def _start_multi_user_http(settings: Settings) -> None:
    """Multi-user HTTP mode: per-JWT-sub Telethon backends.

    Runs the same mcp-core ``run_http_server`` as single-user mode but
    binds ``0.0.0.0:8080`` (deployment behind reverse proxy), wires
    ``auth_scope=_per_request_sub_scope`` to pin per-request user state,
    and routes credential writes through a per-sub
    ``TelegramAuthProvider`` so concurrent users do not share Telethon
    sessions.

    The ``DCR_SERVER_SECRET`` env var is required by the upstream check
    in :func:`_is_multi_user_mode`; mcp-core's local OAuth AS reuses it
    to mint per-user JWTs.
    """
    import asyncio

    from mcp_core.transport.local_server import run_http_server

    from ..auth.telegram_auth_provider import TelegramAuthProvider, set_global_provider
    from ..credential_form import render_telegram_credential_form
    from ..credential_state import on_step_submitted, save_credentials
    from ..server import create_http_mcp_server

    # Set _multi_user_mode = True in server module so get_backend() reads
    # the per-request contextvar set by _per_request_sub_scope below
    # instead of falling back to the global single-user backend.
    mcp = create_http_mcp_server()

    # Build the global TelegramAuthProvider so ``save_credentials``,
    # ``on_step_submitted``, and the auth_scope middleware all share the
    # same per-sub backend cache.
    auth_provider = TelegramAuthProvider(
        settings.data_dir,
        int(settings.api_id or 0),
        settings.api_hash or "",
    )
    set_global_provider(auth_provider)

    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")
    public_url = os.environ.get("PUBLIC_URL", "")

    logger.info("Starting multi-user HTTP server on {}:{}", host, port)
    logger.info("Public URL: {}", public_url)

    async def _run_with_lifecycle() -> None:
        try:
            await auth_provider.restore_sessions()
        except Exception:
            logger.opt(exception=True).warning(
                "Failed to restore Telegram sessions on startup"
            )
        try:
            await run_http_server(
                mcp,
                server_name="better-telegram-mcp",
                relay_schema=RELAY_SCHEMA,
                port=port,
                host=host,
                on_credentials_saved=save_credentials,
                on_step_submitted=on_step_submitted,
                custom_credential_form_html=render_telegram_credential_form,
                auth_scope=_per_request_sub_scope,
            )
        finally:
            try:
                await auth_provider.shutdown()
            except Exception:
                logger.opt(exception=True).warning(
                    "Failed to cleanly shut down TelegramAuthProvider"
                )

    asyncio.run(_run_with_lifecycle())
