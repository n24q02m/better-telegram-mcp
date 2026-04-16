"""Tests for OAuth server transport."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from better_telegram_mcp.transports.oauth_server import create_app


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "keys").mkdir()
    return d


@pytest.fixture
def mock_issuer():
    issuer = MagicMock()
    issuer.get_jwks.return_value = {"keys": []}
    issuer.verify_access_token.return_value = {"sub": "user123"}
    return issuer


@pytest.fixture
def mock_oauth():
    oauth = MagicMock()
    oauth.create_authorize_redirect = AsyncMock(return_value="https://relay/auth")
    oauth.exchange_code = AsyncMock(
        return_value=("access_token_123", {"TELEGRAM_BOT_TOKEN": "123:abc"})
    )
    return oauth


@pytest.fixture
def mock_user_store():
    store = MagicMock()
    store.get_credentials.return_value = {"TELEGRAM_BOT_TOKEN": "123:abc"}
    return store


@pytest.fixture
def mock_auth_provider():
    provider = MagicMock()
    provider.restore_sessions = AsyncMock()
    provider.shutdown = AsyncMock()
    provider.register_bot = AsyncMock()
    provider.resolve_backend.return_value = MagicMock()
    return provider


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
        await send(
            {
                "type": "http.response.body",
                "body": b'{"jsonrpc":"2.0","result":"ok","id":1}',
            }
        )

    return app


@pytest.fixture
def app(
    data_dir, mock_issuer, mock_oauth, mock_user_store, mock_auth_provider, mock_inner_app
):
    with (
        patch(
            "better_telegram_mcp.transports.oauth_server.JWTIssuer",
            return_value=mock_issuer,
        ),
        patch(
            "better_telegram_mcp.transports.oauth_server.OAuthProvider",
            return_value=mock_oauth,
        ),
        patch(
            "better_telegram_mcp.transports.oauth_server.SqliteUserStore",
            return_value=mock_user_store,
        ),
        patch(
            "better_telegram_mcp.auth.telegram_auth_provider.TelegramAuthProvider",
            return_value=mock_auth_provider,
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

            app = create_app(
                data_dir=data_dir,
                public_url="https://mcp.example.com",
                master_secret="topsecret",
            )
            return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


def test_authorize_redirect(client, mock_oauth):
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

    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "https://relay/auth"
    mock_oauth.create_authorize_redirect.assert_called_once()


def test_authorize_error(client, mock_oauth):
    mock_oauth.create_authorize_redirect.side_effect = Exception("failed")
    resp = client.get(
        "/authorize",
        params={
            "client_id": "cli",
            "redirect_uri": "https://cli/cb",
            "state": "st",
            "code_challenge": "cc",
        },
    )
    assert resp.status_code == 500
    assert resp.json()["error"] == "server_error"


def test_authorize_missing_params(client):
    resp = client.get("/authorize", params={"client_id": "cli"})
    assert resp.status_code == 400
    assert resp.json() == {"error": "missing_parameters"}


def test_token_exchange_bot(client, mock_oauth, mock_user_store, mock_auth_provider):
    resp = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": "c123",
            "code_verifier": "v123",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "access_token_123"
    assert data["token_type"] == "Bearer"

    mock_oauth.exchange_code.assert_called_once()
    mock_user_store.save_credentials.assert_called_once()
    mock_auth_provider.register_bot.assert_called_once_with("bot_123", "123:abc")


def test_token_invalid_grant(client, mock_oauth):
    mock_oauth.exchange_code.side_effect = ValueError("invalid_grant")
    resp = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": "c123",
            "code_verifier": "v123",
        },
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "invalid_grant"}


def test_token_error(client, mock_oauth):
    mock_oauth.exchange_code.side_effect = Exception("crash")
    resp = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": "c123",
            "code_verifier": "v123",
        },
    )
    assert resp.status_code == 500
    assert resp.json()["error"] == "server_error"


def test_token_unsupported_grant(client):
    resp = client.post("/token", data={"grant_type": "password"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "unsupported_grant_type"


def test_jwks(client, mock_issuer):
    resp = client.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    assert resp.json() == {"keys": []}


def test_metadata(client):
    resp = client.get("/.well-known/oauth-authorization-server")
    assert resp.status_code == 200
    assert resp.json()["authorization_endpoint"] == "https://mcp.example.com/authorize"


def test_mcp_no_auth(client):
    resp = client.post("/mcp", json={"jsonrpc": "2.0", "method": "list_tools", "id": 1})
    assert resp.status_code == 403
    assert "Bearer authentication required" in resp.json()["error"]["message"]


def test_mcp_invalid_token(client, mock_issuer):
    mock_issuer.verify_access_token.side_effect = Exception("invalid")
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "list_tools", "id": 1},
        headers={"Authorization": "Bearer badtoken"},
    )
    assert resp.status_code == 403
    assert "Invalid or expired access token" in resp.json()["error"]["message"]


def test_mcp_success(client, mock_issuer, mock_auth_provider):
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "list_tools", "id": 1},
        headers={"Authorization": "Bearer goodtoken"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"


def test_mcp_reload_backend(client, mock_issuer, mock_auth_provider, mock_user_store):
    # Initial resolve returns None, then returns a mock backend
    mock_auth_provider.resolve_backend.side_effect = [None, MagicMock()]

    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "list_tools", "id": 1},
        headers={"Authorization": "Bearer goodtoken"},
    )

    assert resp.status_code == 200
    mock_auth_provider.register_bot.assert_called()


def test_mcp_user_not_found(client, mock_issuer, mock_auth_provider, mock_user_store):
    mock_auth_provider.resolve_backend.return_value = None
    mock_user_store.get_credentials.return_value = None

    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "list_tools", "id": 1},
        headers={"Authorization": "Bearer goodtoken"},
    )

    assert resp.status_code == 403
    assert "User credentials not found" in resp.json()["error"]["message"]


def test_lifespan(client, mock_auth_provider):
    # lifespan is covered by TestClient(app) as client
    # We can verify that restore_sessions and shutdown were called
    mock_auth_provider.restore_sessions.assert_called_once()
    # shutdown will be called when the client context ends (fixture yield)
