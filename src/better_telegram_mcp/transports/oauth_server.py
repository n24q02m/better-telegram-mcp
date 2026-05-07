"""Standard OAuth 2.1 ASGI application for multi-user HTTP mode.

Provides:
- GET /authorize - Start OAuth 2.1 PKCE Flow
- POST /token - Exchange code for JWT
- GET /.well-known/jwks.json - JWKS discovery
- POST /mcp - MCP endpoint with JWT Bearer auth -> per-user backend
- GET /mcp - SSE streaming
"""

import hashlib
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast

from loguru import logger

if TYPE_CHECKING:
    from ..auth.telegram_auth_provider import TelegramAuthProvider
from mcp_core.oauth import (
    JWTIssuer,
    OAuthProvider,
    SqliteUserStore,
)
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from ..relay_schema import RELAY_SCHEMA
from .http import _current_backend


def _extract_user_id(creds: dict) -> str:
    """Hash the token or phone to create stable user_id."""
    if creds.get("TELEGRAM_BOT_TOKEN"):
        idt = creds["TELEGRAM_BOT_TOKEN"].split(":")[0]
        return f"bot_{idt}"
    if phone := creds.get("TELEGRAM_PHONE"):
        return f"usr_{phone}"
    return "unknown_user"


async def _exchange_code_and_register(
    oauth: OAuthProvider,
    user_store: SqliteUserStore,
    auth_provider: "TelegramAuthProvider",
    code: str,
    code_verifier: str,
) -> str:
    """Exchange OAuth code for tokens and register backend clients."""
    access_token, credentials = await oauth.exchange_code(
        code, code_verifier, _extract_user_id
    )

    user_id = _extract_user_id(credentials)
    user_store.save_credentials(user_id, credentials)

    # Start backend immediately
    if bot_token := credentials.get("TELEGRAM_BOT_TOKEN"):
        await auth_provider.register_bot(user_id, bot_token)

    return access_token


def _jsonrpc_error(code: int, message: str) -> JSONResponse:
    # RFC 6750 §3: missing/invalid bearer token MUST return 401 with
    # WWW-Authenticate: Bearer. MCP Python SDK relies on this header to
    # discover the authorization server and initiate the OAuth flow; if
    # we return 403 the client treats it as a terminal authorization
    # failure and never attempts to authenticate.
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": None,
        },
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_app(
    *,
    data_dir: Path,
    public_url: str,
    master_secret: str,
) -> Starlette:
    """Create the multi-user Starlette ASGI application with OAuth 2.1."""

    issuer = JWTIssuer(server_name="better-telegram-mcp", keys_dir=data_dir / "keys")
    user_store = SqliteUserStore(
        db_path=data_dir / "users.db",
        master_key=hashlib.sha256(master_secret.encode()).digest(),
    )

    # We must start relay oauth provider
    relay_url = os.environ.get(
        "MCP_RELAY_URL", "https://better-telegram-mcp.n24q02m.com"
    )
    oauth = OAuthProvider(
        server_name="better-telegram-mcp",
        relay_base_url=relay_url,
        relay_schema=RELAY_SCHEMA,
        jwt_issuer=issuer,
    )

    # Track backends
    from ..auth.telegram_auth_provider import TelegramAuthProvider

    # Extract defaults if possible, otherwise rely on credentials.
    # Note: TelegramAuthProvider currently requires api_id/api_hash at init.
    # We will pass dummy/env values; individual backends will use the per-user credentials
    # during `_create_backend` (we'll need to adapt it slightly)
    # For now, telegram_auth_provider handles caching live backends.
    auth_provider = TelegramAuthProvider(
        data_dir,
        int(os.getenv("TELEGRAM_API_ID", 0) or 0),
        os.getenv("TELEGRAM_API_HASH", ""),
    )

    from ..server import create_http_mcp_server

    mcp_server = create_http_mcp_server()

    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    session_manager = StreamableHTTPSessionManager(app=mcp_server._mcp_server)

    @asynccontextmanager
    async def lifespan(app: Starlette):
        await auth_provider.restore_sessions()
        logger.info("OAuth Server started")
        async with session_manager.run():
            yield
        await auth_provider.shutdown()

    async def authorize(request: Request) -> JSONResponse | RedirectResponse:
        """GET /authorize"""
        params = request.query_params
        client_id = params.get("client_id")
        redirect_uri = params.get("redirect_uri")
        state = params.get("state")
        code_challenge = params.get("code_challenge")
        method = params.get("code_challenge_method", "S256")

        if not all([client_id, redirect_uri, state, code_challenge]):
            return JSONResponse({"error": "missing_parameters"}, status_code=400)

        try:
            url = await oauth.create_authorize_redirect(
                client_id=cast(str, client_id),
                redirect_uri=cast(str, redirect_uri),
                state=cast(str, state),
                code_challenge=cast(str, code_challenge),
                code_challenge_method=method,
            )
            return RedirectResponse(url)
        except Exception as e:
            logger.exception("Authorize failed")
            return JSONResponse(
                {"error": "server_error", "description": str(e)}, status_code=500
            )

    async def register(request: Request) -> JSONResponse:
        """POST /register — RFC 7591 Dynamic Client Registration."""
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({"error": "invalid_request"}, status_code=400)

        client_name = body.get("client_name", "unknown")
        redirect_uris = body.get("redirect_uris", [])
        grant_types = body.get("grant_types", ["authorization_code"])
        response_types = body.get("response_types", ["code"])
        token_endpoint_auth_method = body.get("token_endpoint_auth_method", "none")

        client_id = str(uuid.uuid4())
        return JSONResponse(
            {
                "client_id": client_id,
                "client_name": client_name,
                "redirect_uris": redirect_uris,
                "grant_types": grant_types,
                "response_types": response_types,
                "token_endpoint_auth_method": token_endpoint_auth_method,
            },
            status_code=201,
        )

    async def token(request: Request) -> JSONResponse:
        """POST /token"""
        try:
            form = await request.form()
        except Exception:
            return JSONResponse({"error": "invalid_request"}, status_code=400)

        grant_type = form.get("grant_type")
        if grant_type != "authorization_code":
            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

        code = cast(str, form.get("code"))
        code_verifier = cast(str, form.get("code_verifier"))

        if not code or not code_verifier:
            return JSONResponse({"error": "missing_parameters"}, status_code=400)

        try:
            access_token = await _exchange_code_and_register(
                oauth, user_store, auth_provider, code, code_verifier
            )
            return JSONResponse(
                {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
        except ValueError as e:
            msg = str(e)
            if "invalid_grant" in msg:
                return JSONResponse({"error": "invalid_grant"}, status_code=400)
            return JSONResponse(
                {"error": "server_error", "description": msg}, status_code=500
            )
        except Exception as e:
            logger.exception("Token exchange failed")
            return JSONResponse(
                {"error": "server_error", "description": str(e)}, status_code=500
            )

    async def jwks(request: Request) -> JSONResponse:
        """GET /.well-known/jwks.json"""
        return JSONResponse(issuer.get_jwks())

    async def metadata(request: Request) -> JSONResponse:
        """GET /.well-known/oauth-authorization-server"""
        return JSONResponse(
            {
                "issuer": public_url,
                "authorization_endpoint": f"{public_url}/authorize",
                "token_endpoint": f"{public_url}/token",
                "registration_endpoint": f"{public_url}/register",
                "jwks_uri": f"{public_url}/.well-known/jwks.json",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "code_challenge_methods_supported": ["S256", "plain"],
                "token_endpoint_auth_methods_supported": ["none"],
            }
        )

    from mcp.server.fastmcp.server import StreamableHTTPASGIApp

    mcp_asgi_handler = StreamableHTTPASGIApp(session_manager)

    class BearerAuthMCPApp:
        def __init__(self, inner: ASGIApp) -> None:
            self.inner = inner

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] != "http":
                await self.inner(scope, receive, send)
                return

            bearer = None
            headers = Headers(scope=scope)
            auth_str = headers.get("authorization")
            if auth_str and auth_str.lower().startswith("bearer "):
                bearer = auth_str[7:].strip()

            if not bearer:
                resp = _jsonrpc_error(-32000, "Bearer authentication required")
                await resp(scope, receive, send)
                return

            try:
                payload = issuer.verify_access_token(bearer)
                user_id = payload["sub"]
            except Exception:
                resp = _jsonrpc_error(-32000, "Invalid or expired access token")
                await resp(scope, receive, send)
                return

            # Check if backend alive
            backend = auth_provider.resolve_backend(user_id)
            if backend is None:
                # Reload backend from store
                creds = user_store.get_credentials(user_id)
                if not creds:
                    resp = _jsonrpc_error(
                        -32000, "User credentials not found or deleted"
                    )
                    await resp(scope, receive, send)
                    return

                # Re-register bot to spin up client
                if creds.get("TELEGRAM_BOT_TOKEN"):
                    try:
                        await auth_provider.register_bot(
                            user_id, creds["TELEGRAM_BOT_TOKEN"]
                        )
                    except Exception:
                        resp = _jsonrpc_error(-32000, "Failed to start bot backend")
                        await resp(scope, receive, send)
                        return
                backend = auth_provider.resolve_backend(user_id)

            if backend is None:
                resp = _jsonrpc_error(-32000, "Backend unavailable")
                await resp(scope, receive, send)
                return

            token = _current_backend.set(backend)
            try:
                await self.inner(scope, receive, send)
            finally:
                _current_backend.reset(token)

    mcp_app = BearerAuthMCPApp(mcp_asgi_handler)

    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": "better-telegram-mcp"})

    routes = [
        Route("/authorize", authorize, methods=["GET"]),
        Route("/register", register, methods=["POST"]),
        Route("/token", token, methods=["POST"]),
        Route("/.well-known/jwks.json", jwks, methods=["GET"]),
        Route("/.well-known/oauth-authorization-server", metadata, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/mcp", endpoint=mcp_app),
    ]

    return Starlette(
        routes=routes,
        lifespan=lifespan,
    )
