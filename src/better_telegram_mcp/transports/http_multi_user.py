"""Multi-user HTTP application using Starlette/ASGI.

Provides:
- POST /auth/register - Dynamic Client Registration
- POST /auth/bot - Bot token authentication -> bearer
- POST /auth/user/send-code - Start user OTP flow -> bearer + phone_code_hash
- POST /auth/user/verify - Complete OTP verification -> bearer
- POST /mcp - MCP endpoint with Bearer auth -> per-user backend
- GET /mcp - SSE streaming for existing sessions
- DELETE /mcp - Close MCP session
- GET /health - Health check
"""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..auth.stateless_client_store import StatelessClientStore
from ..auth.telegram_auth_provider import TelegramAuthProvider
from .http import _current_backend

# Rate limiting: simple in-memory token bucket per IP
_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_AUTH = 20  # requests per window for auth endpoints
_RATE_LIMIT_MCP = 120  # requests per window for MCP endpoint


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


def create_app(
    *,
    data_dir: Path,
    public_url: str,
    dcr_secret: str,
    api_id: int,
    api_hash: str,
) -> Starlette:
    """Create the multi-user Starlette ASGI application."""

    client_store = StatelessClientStore(dcr_secret)
    auth_provider = TelegramAuthProvider(data_dir, api_id, api_hash)

    # Session -> bearer mapping for ownership check
    session_bearers: dict[str, str] = {}

    @asynccontextmanager
    async def lifespan(app: Starlette):
        """Restore sessions on startup, cleanup on shutdown."""
        restored = await auth_provider.restore_sessions()
        logger.info("Restored {} active sessions", restored)
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

    # --- MCP endpoint ---

    async def mcp_post(request: Request) -> JSONResponse:
        """MCP POST endpoint - new session or existing session messages."""
        ip = _get_client_ip(request)
        if not _check_rate_limit(f"mcp:{ip}", _RATE_LIMIT_MCP):
            return _jsonrpc_error(-32000, "Rate limit exceeded")

        bearer = _extract_bearer(request)
        if not bearer:
            return _jsonrpc_error(-32000, "Bearer authentication required")

        backend = auth_provider.resolve_backend(bearer)
        if backend is None:
            return _jsonrpc_error(
                -32000,
                "Invalid or expired bearer token. Authenticate via /auth/bot or /auth/user/send-code first.",
            )

        # Set per-user backend in context
        token = _current_backend.set(backend)
        try:
            # Ensure multi-user mode is activated
            from ..server import create_http_mcp_server

            create_http_mcp_server()

            # For now, return a JSON-RPC response indicating the tool call should use
            # the streamable HTTP transport. The actual MCP message handling
            # is delegated to FastMCP.
            try:
                body = await request.json()
            except Exception:
                return _jsonrpc_error(-32700, "Parse error")

            # Check session ownership
            session_id = request.headers.get("mcp-session-id")
            if session_id:
                owner = session_bearers.get(session_id)
                if owner and owner != bearer:
                    return _jsonrpc_error(-32000, "Session belongs to a different user")

            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": "Use streamable-http transport at /mcp/sse for MCP protocol",
                    },
                    "id": body.get("id"),
                },
                status_code=200,
            )
        finally:
            _current_backend.reset(token)

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

    routes = [
        Route("/auth/register", register, methods=["POST"]),
        Route("/auth/bot", auth_bot, methods=["POST"]),
        Route("/auth/user/send-code", auth_user_send_code, methods=["POST"]),
        Route("/auth/user/verify", auth_user_verify, methods=["POST"]),
        Route("/mcp", mcp_post, methods=["POST"]),
        Route("/health", health, methods=["GET"]),
    ]

    return Starlette(
        routes=routes,
        lifespan=lifespan,
    )
