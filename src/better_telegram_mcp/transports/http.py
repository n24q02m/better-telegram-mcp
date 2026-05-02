"""HTTP transport mode for better-telegram-mcp.

Two outcomes:
- Multi-user OAuth 2.1 (deployed) when ``DCR_SERVER_SECRET`` + ``PUBLIC_URL``
  + a Telegram ``api_id``/``api_hash`` pair are present. Per-JWT-sub
  Telethon clients, isolated credentials. Intended for public deploys.
- Single-user paste-form fallback for self-host / localhost. Same browser
  paste-form flow as the other plugins (notion, email, wet, mnemo, crg) —
  uses ``run_http_server`` from mcp-core so /authorize renders the custom
  Telegram credential form and OTP/2FA flow runs against ``/otp``.

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

from loguru import logger

from ..config import Settings
from ..relay_schema import RELAY_SCHEMA

# ContextVar for per-user backend injection in multi-user HTTP mode
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


def _start_multi_user_http(settings: Settings) -> None:
    """Multi-user HTTP mode: per-user auth with standard OAuth 2.1."""

    import uvicorn

    from .oauth_server import create_app

    port = int(os.environ.get("PORT", "8080"))
    public_url = os.environ["PUBLIC_URL"]
    master_secret = settings.secret

    app = create_app(
        data_dir=settings.data_dir,
        public_url=public_url,
        master_secret=master_secret,
    )

    logger.info("Starting multi-user OAuth HTTP server on port {}", port)
    logger.info("Public URL: {}", public_url)

    # Default to 127.0.0.1 for safety; override via HOST env var (e.g. Docker sets HOST=0.0.0.0)
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port, log_level="info")
