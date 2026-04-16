"""Standard OAuth 2.1 ASGI application for multi-user HTTP mode.

Provides:
- GET /authorize - Start OAuth 2.1 PKCE Flow
- POST /token - Exchange code for JWT
- GET /.well-known/jwks.json - JWKS discovery
- POST /mcp - MCP endpoint with JWT Bearer auth -> per-user backend
- GET /mcp - SSE streaming
"""

from __future__ import annotations

import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast

from loguru import logger
from mcp_core.oauth import (
    JWTIssuer,
    OAuthProvider,
    SqliteUserStore,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from ..relay_schema import RELAY_SCHEMA
from .http import _current_backend

if TYPE_CHECKING:
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    from ..auth.telegram_auth_provider import TelegramAuthProvider


def _jsonrpc_error(code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": None,
        },
        status_code=403,  # Authentication errors map to JSON-RPC HTTP 403 or 401
    )


class BearerAuthMCPApp:
    def __init__(
        self,
        inner: ASGIApp,
        issuer: JWTIssuer,
        auth_provider: TelegramAuthProvider,
        user_store: SqliteUserStore,
    ) -> None:
        self.inner = inner
        self.issuer = issuer
        self.auth_provider = auth_provider
        self.user_store = user_store

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.inner(scope, receive, send)
            return

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

        try:
            payload = self.issuer.verify_access_token(bearer)
            user_id = payload["sub"]
        except Exception:
            resp = _jsonrpc_error(-32000, "Invalid or expired access token")
            await resp(scope, receive, send)
            return

        # Check if backend alive
        backend = self.auth_provider.resolve_backend(user_id)
        if backend is None:
            # Reload backend from store
            creds = self.user_store.get_credentials(user_id)
            if not creds:
                resp = _jsonrpc_error(-32000, "User credentials not found or deleted")
                await resp(scope, receive, send)
                return

            # Re-register bot to spin up client
            if creds.get("TELEGRAM_BOT_TOKEN"):
                try:
                    await self.auth_provider.register_bot(
                        user_id, creds["TELEGRAM_BOT_TOKEN"]
                    )
                except Exception:
                    resp = _jsonrpc_error(-32000, "Failed to start bot backend")
                    await resp(scope, receive, send)
                    return
            backend = self.auth_provider.resolve_backend(user_id)

        if backend is None:
            resp = _jsonrpc_error(-32000, "Backend unavailable")
            await resp(scope, receive, send)
            return

        token = _current_backend.set(backend)
        try:
            await self.inner(scope, receive, send)
        finally:
            _current_backend.reset(token)


class OAuthServer:
    def __init__(
        self,
        issuer: JWTIssuer,
        user_store: SqliteUserStore,
        oauth: OAuthProvider,
        auth_provider: TelegramAuthProvider,
        public_url: str,
        session_manager: StreamableHTTPSessionManager,
    ):
        self.issuer = issuer
        self.user_store = user_store
        self.oauth = oauth
        self.auth_provider = auth_provider
        self.public_url = public_url
        self.session_manager = session_manager

    @asynccontextmanager
    async def lifespan(self, app: Starlette):
        await self.auth_provider.restore_sessions()
        logger.info("OAuth Server started")
        async with self.session_manager.run():
            yield
        await self.auth_provider.shutdown()

    async def authorize(self, request: Request) -> JSONResponse | RedirectResponse:
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
            url = await self.oauth.create_authorize_redirect(
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

    async def token(self, request: Request) -> JSONResponse:
        """POST /token"""
        try:
            form = await request.form()
        except Exception:
            return JSONResponse({"error": "invalid_request"}, status_code=400)

        grant_type = form.get("grant_type")
        if grant_type != "authorization_code":
            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

        code = form.get("code")
        code_verifier = form.get("code_verifier")

        if not code or not code_verifier:
            return JSONResponse({"error": "missing_parameters"}, status_code=400)

        def extract_user_id(creds: dict) -> str:
            # Hash the token or phone to create stable user_id
            if creds.get("TELEGRAM_BOT_TOKEN"):
                idt = creds["TELEGRAM_BOT_TOKEN"].split(":")[0]
                return f"bot_{idt}"
            elif creds.get("TELEGRAM_PHONE"):
                return f"usr_{creds.get('TELEGRAM_PHONE')}"
            return "unknown_user"

        try:
            access_token, credentials = await self.oauth.exchange_code(
                cast(str, code), cast(str, code_verifier), extract_user_id
            )

            user_id = extract_user_id(credentials)
            self.user_store.save_credentials(user_id, credentials)

            # Start backend immediately
            if credentials.get("TELEGRAM_BOT_TOKEN"):
                await self.auth_provider.register_bot(
                    user_id, credentials["TELEGRAM_BOT_TOKEN"]
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

    async def jwks(self, request: Request) -> JSONResponse:
        """GET /.well-known/jwks.json"""
        return JSONResponse(self.issuer.get_jwks())

    async def metadata(self, request: Request) -> JSONResponse:
        """GET /.well-known/oauth-authorization-server"""
        return JSONResponse(
            {
                "issuer": self.public_url,
                "authorization_endpoint": f"{self.public_url}/authorize",
                "token_endpoint": f"{self.public_url}/token",
                "jwks_uri": f"{self.public_url}/.well-known/jwks.json",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "code_challenge_methods_supported": ["S256", "plain"],
                "token_endpoint_auth_methods_supported": ["none"],
            }
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

    auth_provider = TelegramAuthProvider(
        data_dir,
        int(os.getenv("TELEGRAM_API_ID", 0) or 0),
        os.getenv("TELEGRAM_API_HASH", ""),
    )

    from ..server import create_http_mcp_server

    mcp_server = create_http_mcp_server()

    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    session_manager = StreamableHTTPSessionManager(app=mcp_server._mcp_server)

    server = OAuthServer(
        issuer=issuer,
        user_store=user_store,
        oauth=oauth,
        auth_provider=auth_provider,
        public_url=public_url,
        session_manager=session_manager,
    )

    from mcp.server.fastmcp.server import StreamableHTTPASGIApp

    mcp_asgi_handler = StreamableHTTPASGIApp(session_manager)
    mcp_app = BearerAuthMCPApp(
        mcp_asgi_handler,
        issuer=issuer,
        auth_provider=auth_provider,
        user_store=user_store,
    )

    routes = [
        Route("/authorize", server.authorize, methods=["GET"]),
        Route("/token", server.token, methods=["POST"]),
        Route("/.well-known/jwks.json", server.jwks, methods=["GET"]),
        Route(
            "/.well-known/oauth-authorization-server", server.metadata, methods=["GET"]
        ),
        Route("/mcp", endpoint=mcp_app),
    ]

    return Starlette(
        routes=routes,
        lifespan=server.lifespan,
    )
