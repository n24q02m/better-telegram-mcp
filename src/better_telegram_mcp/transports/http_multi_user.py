"""Multi-user HTTP application using Starlette/ASGI.

Provides:
- POST /auth/register - Dynamic Client Registration
- POST /auth/bot - Bot token authentication -> bearer
- POST /auth/user/send-code - Start user OTP flow -> bearer + phone_code_hash
- POST /auth/user/verify - Complete OTP verification -> bearer
- POST /mcp - MCP action endpoint with Bearer auth -> per-user backend
- GET /events/telegram - Unified bearer-authenticated SSE stream
- GET /health - Health check
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from ..auth.stateless_client_store import StatelessClientStore
from ..auth.telegram_auth_provider import TelegramAuthProvider
from ..config import Settings
from .http import _current_backend

# Rate limiting: simple in-memory token bucket per IP
_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_AUTH = 20  # requests per window for auth endpoints
_RATE_LIMIT_MCP = 120  # requests per window for MCP endpoint
_MAX_RATE_LIMIT_KEYS = 10_000


def _check_rate_limit(ip: str, limit: int) -> bool:
    """Check if IP is within rate limit. Returns True if allowed."""
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW
    timestamps = _rate_limits[ip]

    # Prune old entries
    _rate_limits[ip] = [t for t in timestamps if t > window_start]

    if len(_rate_limits[ip]) >= limit:
        return False

    _rate_limits[ip].append(now)

    # Periodic eviction: remove stale keys when dict grows too large
    if len(_rate_limits) > _MAX_RATE_LIMIT_KEYS:
        stale_keys = [
            key for key, ts in _rate_limits.items() if not ts or ts[-1] <= window_start
        ]
        for key in stale_keys:
            del _rate_limits[key]

    return True


def _get_client_ip(request: Request) -> str:
    """Safely extract client IP, respecting reverse proxies if headers are present."""
    if "cf-connecting-ip" in request.headers:
        return request.headers["cf-connecting-ip"]
    if "x-forwarded-for" in request.headers:
        # X-Forwarded-For can be a comma-separated list of IPs; the first is the client
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_bearer(request: Request) -> str | None:
    """Extract bearer token from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def _error_response(status: int, error: str, description: str) -> JSONResponse:
    return JSONResponse(
        {"error": error, "error_description": description},
        status_code=status,
    )


def _jsonrpc_error(code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": None,
        },
        status_code=403,
    )


def _format_sse_event(
    *, event: str, data: dict[str, object], event_id: str | None = None
) -> bytes:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, separators=(',', ':'))}")
    lines.append("")
    return "\n".join(lines).encode("utf-8") + b"\n"


def create_app(
    *,
    data_dir: Path,
    public_url: str,
    dcr_secret: str,
    api_id: int,
    api_hash: str,
    runtime_settings: Settings | None = None,
) -> Starlette:
    """Create the multi-user Starlette ASGI application."""

    _rate_limits.clear()

    client_store = StatelessClientStore(dcr_secret)
    auth_provider = TelegramAuthProvider(
        data_dir,
        api_id,
        api_hash,
        runtime_settings=runtime_settings,
    )

    # Create MCP server and session manager for streamable-http
    from ..server import create_http_mcp_server

    mcp_server = create_http_mcp_server()

    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    session_manager = StreamableHTTPSessionManager(app=mcp_server._mcp_server)

    @asynccontextmanager
    async def lifespan(app: Starlette):
        """Restore sessions on startup, start MCP session manager, cleanup on shutdown."""
        restored = await auth_provider.restore_sessions()
        logger.info("Restored {} active sessions", restored)
        async with session_manager.run():
            yield
        await auth_provider.shutdown()

    # --- Auth endpoints ---

    async def register(request: Request) -> JSONResponse:
        """Dynamic Client Registration endpoint."""
        ip = _get_client_ip(request)
        if not _check_rate_limit(f"auth:{ip}", _RATE_LIMIT_AUTH):
            return _error_response(429, "rate_limited", "Too many requests")

        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "invalid_request", "Invalid JSON body")

        redirect_uris = body.get("redirect_uris", [])
        if not isinstance(redirect_uris, list):
            return _error_response(
                400, "invalid_request", "redirect_uris must be a list"
            )

        client_name = body.get("client_name")
        client_id, client_secret = client_store.register(redirect_uris, client_name)

        return JSONResponse(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "client_name": client_name,
                "redirect_uris": redirect_uris,
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
            },
            status_code=201,
        )

    async def auth_bot(request: Request) -> JSONResponse:
        """Bot token authentication endpoint.

        Accepts bot_token, validates it with Telegram, returns bearer.
        """
        ip = _get_client_ip(request)
        if not _check_rate_limit(f"auth:{ip}", _RATE_LIMIT_AUTH):
            return _error_response(429, "rate_limited", "Too many requests")

        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "invalid_request", "Invalid JSON body")

        bot_token = body.get("bot_token")
        if not bot_token or not isinstance(bot_token, str):
            return _error_response(400, "invalid_request", "bot_token is required")

        try:
            bearer = await auth_provider.register_bot("", bot_token)
        except ValueError as exc:
            return _error_response(401, "invalid_token", str(exc))

        return JSONResponse(
            {
                "bearer_token": bearer,
                "token_type": "Bearer",
                "mode": "bot",
            }
        )

    async def auth_user_send_code(request: Request) -> JSONResponse:
        """Start user authentication - send OTP code to phone."""
        ip = _get_client_ip(request)
        if not _check_rate_limit(f"auth:{ip}", _RATE_LIMIT_AUTH):
            return _error_response(429, "rate_limited", "Too many requests")

        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "invalid_request", "Invalid JSON body")

        phone = body.get("phone")
        if not phone or not isinstance(phone, str):
            return _error_response(
                400, "invalid_request", "phone is required (international format)"
            )

        try:
            result = await auth_provider.start_user_auth("", phone)
        except ValueError as exc:
            return _error_response(400, "auth_error", str(exc))

        return JSONResponse(
            {
                "bearer_token": result["bearer"],
                "phone_code_hash": result["phone_code_hash"],
                "message": "Check Telegram for OTP code",
            }
        )

    async def auth_user_verify(request: Request) -> JSONResponse:
        """Complete user authentication with OTP code."""
        ip = _get_client_ip(request)
        if not _check_rate_limit(f"auth:{ip}", _RATE_LIMIT_AUTH):
            return _error_response(429, "rate_limited", "Too many requests")

        bearer = _extract_bearer(request)
        if not bearer:
            return _error_response(
                401, "unauthorized", "Bearer token required (from send-code step)"
            )

        try:
            body = await request.json()
        except Exception:
            return _error_response(400, "invalid_request", "Invalid JSON body")

        code = body.get("code")
        if not code or not isinstance(code, str):
            return _error_response(400, "invalid_request", "code is required")

        password = body.get("password")

        try:
            result = await auth_provider.complete_user_auth(
                bearer, code, password=password
            )
        except ValueError as exc:
            return _error_response(400, "auth_error", str(exc))

        return JSONResponse(
            {
                "bearer_token": bearer,
                "token_type": "Bearer",
                "mode": "user",
                **result,
            }
        )

    # --- MCP endpoint (bearer auth + per-user backend injection) ---

    from mcp.server.fastmcp.server import StreamableHTTPASGIApp

    mcp_asgi_handler = StreamableHTTPASGIApp(session_manager)

    class BearerAuthMCPApp:
        """ASGI middleware: authenticate bearer -> inject per-user backend -> forward to MCP."""

        def __init__(self, inner: ASGIApp) -> None:
            self.inner = inner

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] != "http":
                await self.inner(scope, receive, send)
                return

            if scope.get("method") != "POST":
                resp = JSONResponse(
                    {
                        "error": "method_not_allowed",
                        "error_description": "/mcp supports POST only",
                    },
                    status_code=405,
                )
                await resp(scope, receive, send)
                return

            # Extract bearer from headers
            bearer = None
            for key, value in scope.get("headers", []):
                if key == b"authorization":
                    auth_str = value.decode("utf-8", errors="ignore")
                    if auth_str.startswith("Bearer "):
                        bearer = auth_str[7:].strip()
                    break

            if not bearer:
                resp = _jsonrpc_error(-32000, "Bearer authentication required")
                await resp(scope, receive, send)
                return

            backend = auth_provider.resolve_backend(bearer)
            if backend is None:
                resp = _jsonrpc_error(
                    -32000,
                    "Invalid or expired bearer token. "
                    "Authenticate via /auth/bot or /auth/user/send-code first.",
                )
                await resp(scope, receive, send)
                return

            token = _current_backend.set(backend)
            try:
                await self.inner(scope, receive, send)
            finally:
                _current_backend.reset(token)

    mcp_app = BearerAuthMCPApp(mcp_asgi_handler)

    async def health(request: Request) -> JSONResponse:
        """Health check endpoint."""
        active = len(auth_provider.active_clients)
        return JSONResponse(
            {
                "status": "ok",
                "mode": "multi-user",
                "active_sessions": active,
                "timestamp": time.time(),
            }
        )

    async def telegram_events(request: Request) -> StreamingResponse | JSONResponse:
        """Bearer-authenticated SSE stream for real-time Telegram events.

        Contract:
        - Events carry ``id:`` fields (SHA256 event_id from the envelope).
        - ``Last-Event-ID`` on reconnect is acknowledged but NOT replayed.
          The server does not maintain a replay buffer. Clients that require
          exactly-once delivery must track ``event_id`` externally.
        - A ``retry:`` hint is sent at stream start.
        """
        bearer = _extract_bearer(request)
        if not bearer:
            return _error_response(401, "unauthorized", "Bearer token required")

        runtime = auth_provider.resolve_runtime(bearer)
        if runtime is None:
            return _error_response(
                401, "unauthorized", "Invalid or expired bearer token"
            )

        last_event_id = request.headers.get("last-event-id")
        if last_event_id is not None:
            logger.debug(
                "SSE reconnect with Last-Event-ID={} (replay not supported, ignored)",
                last_event_id,
            )

        subscriber = runtime.hub.subscribe()
        heartbeat_seconds = (
            auth_provider.runtime_settings.sse_heartbeat_seconds
            if auth_provider.runtime_settings is not None
            else 15
        )

        async def event_stream():
            try:
                yield f"retry: {heartbeat_seconds * 1000}\n\n".encode()
                while True:
                    try:
                        item = await asyncio.wait_for(
                            subscriber.next_item(), timeout=heartbeat_seconds
                        )
                    except TimeoutError:
                        yield b"event: heartbeat\ndata: {}\n\n"
                        continue

                    if item.kind == "event":
                        event = item.event or {}
                        event_id = event.get("event_id")
                        event_type = str(event.get("event_type", "message"))
                        yield _format_sse_event(
                            event=event_type,
                            data=event,
                            event_id=None if event_id is None else str(event_id),
                        )
                        continue

                    reason = item.reason or "runtime_stopped"
                    yield _format_sse_event(event="error", data={"reason": reason})
                    break
            finally:
                runtime.hub.unsubscribe(subscriber)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    routes = [
        Route("/auth/register", register, methods=["POST"]),
        Route("/auth/bot", auth_bot, methods=["POST"]),
        Route("/auth/user/send-code", auth_user_send_code, methods=["POST"]),
        Route("/auth/user/verify", auth_user_verify, methods=["POST"]),
        Route("/events/telegram", telegram_events, methods=["GET"]),
        Route("/mcp", endpoint=mcp_app),
        Route("/health", health, methods=["GET"]),
    ]

    app = Starlette(
        routes=routes,
        lifespan=lifespan,
    )
    app.state.auth_provider = auth_provider
    return app
