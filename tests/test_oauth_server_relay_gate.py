"""Tests for the relay-password gate wired into the multi-user OAuth server.

Per spec ``2026-05-01-stdio-pure-http-multiuser §5.1.2.1`` + D21, the custom
multi-user ``oauth_server.create_app`` must mount ``/login`` GET + POST and
gate ``/authorize`` behind the ``MCP_RELAY_PASSWORD`` cookie session — same
primitive mcp-core's ``local_oauth_app.py`` uses, so single-user and
multi-user deployments share an identical edge auth surface.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp_core.auth.relay_login import _fails, _sessions, configure_relay_login
from starlette.testclient import TestClient

from better_telegram_mcp.transports.oauth_server import create_app


@pytest.fixture(autouse=True)
def _reset_relay_login() -> None:
    """Clear module-scoped session + brute-force counters between cases.

    ``relay_login`` keeps these in module-global dicts; without a reset
    a sticky ``mcp_relay_session`` from one test can satisfy the gate in
    another, masking real failures.
    """
    _sessions.clear()
    _fails.clear()
    configure_relay_login("")
    yield
    _sessions.clear()
    _fails.clear()
    configure_relay_login("")


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "keys").mkdir()
    return d


@pytest.fixture
def mock_inner_app():
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b"{}"})

    return app


def _build_app(data_dir, mock_inner_app, *, relay_password: str | None):
    """Build the multi-user OAuth app with optional ``MCP_RELAY_PASSWORD`` set.

    The env var must be set BEFORE ``create_app`` is called — the wiring
    snapshots ``os.environ.get("MCP_RELAY_PASSWORD", "")`` at construction
    time and feeds it into ``configure_relay_login``.
    """
    issuer = MagicMock()
    issuer.get_jwks.return_value = {"keys": []}
    issuer.verify_access_token.return_value = {"sub": "user123"}

    oauth = MagicMock()
    oauth.create_authorize_redirect = AsyncMock(return_value="https://relay/auth")
    oauth.exchange_code = AsyncMock(
        return_value=("access_token_123", {"TELEGRAM_BOT_TOKEN": "123:abc"})
    )

    user_store = MagicMock()
    user_store.get_credentials.return_value = {"TELEGRAM_BOT_TOKEN": "123:abc"}

    auth_provider = MagicMock()
    auth_provider.restore_sessions = AsyncMock()
    auth_provider.shutdown = AsyncMock()
    auth_provider.register_bot = AsyncMock()
    auth_provider.resolve_backend.return_value = MagicMock()

    env_patch = (
        patch.dict("os.environ", {"MCP_RELAY_PASSWORD": relay_password}, clear=False)
        if relay_password is not None
        else patch.dict("os.environ", {}, clear=False)
    )

    with (
        env_patch,
        patch(
            "better_telegram_mcp.transports.oauth_server.JWTIssuer",
            return_value=issuer,
        ),
        patch(
            "better_telegram_mcp.transports.oauth_server.OAuthProvider",
            return_value=oauth,
        ),
        patch(
            "better_telegram_mcp.transports.oauth_server.SqliteUserStore",
            return_value=user_store,
        ),
        patch(
            "better_telegram_mcp.auth.telegram_auth_provider.TelegramAuthProvider",
            return_value=auth_provider,
        ),
        patch(
            "better_telegram_mcp.server.create_http_mcp_server"
        ) as mock_create_server,
    ):
        mock_mcp = MagicMock()
        mock_mcp._mcp_server = MagicMock()
        mock_create_server.return_value = mock_mcp

        with (
            patch(
                "mcp.server.streamable_http_manager.StreamableHTTPSessionManager"
            ) as mock_manager_cls,
            patch(
                "mcp.server.fastmcp.server.StreamableHTTPASGIApp",
                return_value=mock_inner_app,
            ),
        ):
            mock_manager = MagicMock()

            @asynccontextmanager
            async def mock_run():
                yield

            mock_manager.run.return_value = mock_run()
            mock_manager_cls.return_value = mock_manager

            return create_app(
                data_dir=data_dir,
                public_url="https://mcp.example.com",
                master_secret="topsecret",
            )


def test_authorize_no_password_gate_disabled(data_dir, mock_inner_app, monkeypatch):
    """Empty MCP_RELAY_PASSWORD -> /authorize proceeds without cookie."""
    monkeypatch.delenv("MCP_RELAY_PASSWORD", raising=False)
    app = _build_app(data_dir, mock_inner_app, relay_password=None)
    with TestClient(app) as client:
        resp = client.get(
            "/authorize",
            params={
                "client_id": "cli",
                "redirect_uri": "https://cli/cb",
                "state": "st",
                "code_challenge": "cc",
            },
            follow_redirects=False,
        )
    # Gate disabled -> falls through to OAuth provider redirect (302/307 to relay).
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "https://relay/auth"


def test_authorize_with_password_no_cookie_redirects_to_login(data_dir, mock_inner_app):
    """MCP_RELAY_PASSWORD set + no cookie -> 302 redirect to /login?next=..."""
    app = _build_app(data_dir, mock_inner_app, relay_password="s3cret")
    with TestClient(app) as client:
        resp = client.get(
            "/authorize",
            params={
                "client_id": "cli",
                "redirect_uri": "https://cli/cb",
                "state": "st",
                "code_challenge": "cc",
            },
            follow_redirects=False,
        )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("/login?next=")
    # The next param must encode the original /authorize URL with query string.
    assert "%2Fauthorize" in location


def test_login_get_returns_html_form(data_dir, mock_inner_app):
    """GET /login -> 200 with the relay-password form."""
    app = _build_app(data_dir, mock_inner_app, relay_password="s3cret")
    with TestClient(app) as client:
        resp = client.get("/login")
    assert resp.status_code == 200
    assert "Relay login" in resp.text
    assert 'name="password"' in resp.text


def test_login_post_wrong_password_401(data_dir, mock_inner_app):
    """POST /login with wrong password -> 401."""
    app = _build_app(data_dir, mock_inner_app, relay_password="s3cret")
    with TestClient(app) as client:
        resp = client.post(
            "/login",
            data={"password": "wrong", "next": "/authorize"},
        )
    assert resp.status_code == 401


def test_login_post_correct_password_sets_cookie_and_redirects(
    data_dir, mock_inner_app
):
    """POST /login with correct password -> 302 + Set-Cookie mcp_relay_session."""
    app = _build_app(data_dir, mock_inner_app, relay_password="s3cret")
    with TestClient(app) as client:
        resp = client.post(
            "/login",
            data={"password": "s3cret", "next": "/authorize"},
            follow_redirects=False,
        )
    assert resp.status_code == 302
    set_cookie = resp.headers.get("set-cookie", "")
    assert "mcp_relay_session=" in set_cookie
    assert resp.headers["location"] == "/authorize"
