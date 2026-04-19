import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.responses import Response
from starlette.testclient import TestClient

from better_telegram_mcp.transports.http_multi_user import (
    _check_rate_limit,
    _error_response,
    _extract_bearer,
    _get_client_ip,
    _jsonrpc_error,
    create_app,
)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from better_telegram_mcp.transports.http_multi_user import _rate_limits

    _rate_limits.clear()


def test_check_rate_limit():
    ip = "127.0.0.1"
    limit = 2
    # First two should pass
    assert _check_rate_limit(ip, limit) is True
    assert _check_rate_limit(ip, limit) is True
    # Third should fail
    assert _check_rate_limit(ip, limit) is False

    # Test window pruning
    with patch("time.time", return_value=time.time() + 61):
        assert _check_rate_limit(ip, limit) is True


def test_get_client_ip():
    request = MagicMock()
    request.client.host = "1.2.3.4"
    request.headers = {}

    # Basic IP
    assert _get_client_ip(request) == "1.2.3.4"

    # Unknown client
    request.client = None
    assert _get_client_ip(request) == "unknown"


def test_get_client_ip_trusted_proxy():
    request = MagicMock()
    request.client.host = "10.0.0.1"
    request.headers = {
        "cf-connecting-ip": "1.1.1.1",
        "x-forwarded-for": "2.2.2.2, 10.0.0.1",
    }

    with patch.dict("os.environ", {"TELEGRAM_TRUSTED_PROXIES": "10.0.0.1"}):
        # Prefers cf-connecting-ip
        assert _get_client_ip(request) == "1.1.1.1"

        # Falls back to x-forwarded-for
        del request.headers["cf-connecting-ip"]
        assert _get_client_ip(request) == "2.2.2.2"


def test_extract_bearer():
    request = MagicMock()
    request.headers = {"authorization": "Bearer my-token"}
    assert _extract_bearer(request) == "my-token"

    request.headers = {"authorization": "bearer my-token"}
    assert _extract_bearer(request) == "my-token"

    request.headers = {"authorization": "BEARER my-token"}
    assert _extract_bearer(request) == "my-token"

    request.headers = {"authorization": "Basic something"}
    assert _extract_bearer(request) is None

    request.headers = {}
    assert _extract_bearer(request) is None


def test_error_responses():
    resp = _error_response(400, "err", "desc")
    assert resp.status_code == 400
    assert b"err" in resp.body

    resp = _jsonrpc_error(-32000, "msg")
    assert resp.status_code == 403
    assert b"msg" in resp.body


# --- App Tests ---


@pytest.fixture
def mock_deps():
    with (
        patch(
            "better_telegram_mcp.transports.http_multi_user.StatelessClientStore"
        ) as m_store,
        patch(
            "better_telegram_mcp.transports.http_multi_user.TelegramAuthProvider"
        ) as m_auth,
        patch("better_telegram_mcp.server.create_http_mcp_server") as m_server,
        patch(
            "mcp.server.streamable_http_manager.StreamableHTTPSessionManager"
        ) as m_mgr,
        patch("mcp.server.fastmcp.server.StreamableHTTPASGIApp") as m_asgi,
    ):
        # Setup mocks
        m_auth_inst = m_auth.return_value
        m_auth_inst.restore_sessions = AsyncMock(return_value=5)
        m_auth_inst.shutdown = AsyncMock()
        m_auth_inst.active_clients = {}
        m_auth_inst.register_bot = AsyncMock(return_value="bearer-token")
        m_auth_inst.start_user_auth = AsyncMock(
            return_value={"bearer": "b1", "phone_code_hash": "h1"}
        )
        m_auth_inst.complete_user_auth = AsyncMock(return_value={"user": "me"})

        m_store_inst = m_store.return_value
        m_store_inst.register.return_value = ("client_id", "client_secret")

        m_mgr_inst = m_mgr.return_value
        m_mgr_inst.run.return_value.__aenter__ = AsyncMock()
        m_mgr_inst.run.return_value.__aexit__ = AsyncMock()

        m_asgi.return_value = MagicMock(
            side_effect=lambda scope, receive, send: Response("mcp-ok")(
                scope, receive, send
            )
        )

        yield {
            "store": m_store_inst,
            "auth": m_auth_inst,
            "server": m_server.return_value,
            "mgr": m_mgr_inst,
            "asgi": m_asgi.return_value,
        }


@pytest.fixture
def client(mock_deps, tmp_path):
    app = create_app(
        data_dir=tmp_path,
        public_url="https://example.com",
        dcr_secret="secret",
        api_id=123,
        api_hash="hash",
    )
    return TestClient(app)


def test_health(client, mock_deps):
    mock_deps["auth"].active_clients = {"t1": MagicMock()}
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["active_sessions"] == 1


def test_register_success(client, mock_deps):
    response = client.post(
        "/auth/register",
        json={"redirect_uris": ["https://app.com"], "client_name": "Test"},
    )
    assert response.status_code == 201
    assert response.json()["client_id"] == "client_id"
    mock_deps["store"].register.assert_called_once_with(["https://app.com"], "Test")


def test_register_invalid_json(client):
    response = client.post("/auth/register", content="invalid")
    assert response.status_code == 400
    assert "invalid_request" in response.json()["error"]


def test_register_invalid_uris(client):
    response = client.post("/auth/register", json={"redirect_uris": "not-a-list"})
    assert response.status_code == 400
    assert "redirect_uris must be a list" in response.json()["error_description"]


def test_auth_bot_success(client, mock_deps):
    response = client.post("/auth/bot", json={"bot_token": "123:abc"})
    assert response.status_code == 200
    assert response.json()["bearer_token"] == "bearer-token"


def test_auth_bot_invalid_token(client, mock_deps):
    mock_deps["auth"].register_bot = AsyncMock(
        side_effect=ValueError("invalid bot token")
    )
    response = client.post("/auth/bot", json={"bot_token": "wrong"})
    assert response.status_code == 401
    assert "invalid_token" in response.json()["error"]


def test_auth_user_send_code_success(client, mock_deps):
    response = client.post("/auth/user/send-code", json={"phone": "+123456789"})
    assert response.status_code == 200
    assert response.json()["bearer_token"] == "b1"


def test_auth_user_send_code_error(client, mock_deps):
    mock_deps["auth"].start_user_auth = AsyncMock(
        side_effect=ValueError("failed to send")
    )
    response = client.post("/auth/user/send-code", json={"phone": "+123456789"})
    assert response.status_code == 400
    assert "auth_error" in response.json()["error"]


def test_auth_user_verify_success(client, mock_deps):
    response = client.post(
        "/auth/user/verify",
        json={"code": "12345"},
        headers={"authorization": "Bearer my-bearer"},
    )
    assert response.status_code == 200
    assert response.json()["user"] == "me"


def test_auth_user_verify_no_bearer(client):
    response = client.post("/auth/user/verify", json={"code": "12345"})
    assert response.status_code == 401
    assert "unauthorized" in response.json()["error"]


def test_mcp_middleware_no_auth(client):
    response = client.post("/mcp", json={})
    assert response.status_code == 403
    assert "Bearer authentication required" in response.json()["error"]["message"]


def test_mcp_middleware_invalid_bearer(client, mock_deps):
    mock_deps["auth"].resolve_backend.return_value = None
    response = client.post("/mcp", json={}, headers={"authorization": "Bearer invalid"})
    assert response.status_code == 403
    assert "Invalid or expired bearer token" in response.json()["error"]["message"]


def test_mcp_middleware_success(client, mock_deps):
    mock_backend = MagicMock()
    mock_deps["auth"].resolve_backend.return_value = mock_backend

    from better_telegram_mcp.transports.http import get_current_backend

    def check_context(scope, receive, send):
        if get_current_backend() == mock_backend:
            return Response("context-ok")(scope, receive, send)
        return Response("context-fail", status_code=500)(scope, receive, send)

    mock_deps["asgi"].side_effect = check_context

    response = client.post("/mcp", json={}, headers={"authorization": "Bearer valid"})
    assert response.status_code == 200
    assert response.text == "context-ok"


def test_lifespan(tmp_path, mock_deps):
    app = create_app(
        data_dir=tmp_path,
        public_url="https://example.com",
        dcr_secret="secret",
        api_id=123,
        api_hash="hash",
    )

    with TestClient(app):
        # lifespan __aenter__ should have run
        mock_deps["auth"].restore_sessions.assert_called_once()
        mock_deps["mgr"].run.assert_called_once()

    # lifespan __aexit__ should have run
    mock_deps["auth"].shutdown.assert_called_once()


def test_rate_limit_enforcement(client):
    for _ in range(20):
        client.post("/auth/register", json={})

    response = client.post("/auth/register", json={})
    assert response.status_code == 429


def test_auth_bot_rate_limited(client):
    for _ in range(20):
        client.post("/auth/bot", json={"bot_token": "123:abc"})
    response = client.post("/auth/bot", json={"bot_token": "123:abc"})
    assert response.status_code == 429


def test_auth_bot_invalid_json(client):
    response = client.post("/auth/bot", content="invalid")
    assert response.status_code == 400


def test_auth_bot_missing_token(client):
    response = client.post("/auth/bot", json={})
    assert response.status_code == 400


def test_auth_user_send_code_rate_limited(client):
    for _ in range(20):
        client.post("/auth/user/send-code", json={"phone": "+123"})
    response = client.post("/auth/user/send-code", json={"phone": "+123"})
    assert response.status_code == 429


def test_auth_user_send_code_invalid_json(client):
    response = client.post("/auth/user/send-code", content="invalid")
    assert response.status_code == 400


def test_auth_user_send_code_missing_phone(client):
    response = client.post("/auth/user/send-code", json={})
    assert response.status_code == 400


def test_auth_user_verify_rate_limited(client):
    for _ in range(20):
        client.post(
            "/auth/user/verify",
            json={"code": "123"},
            headers={"authorization": "Bearer b"},
        )
    response = client.post(
        "/auth/user/verify", json={"code": "123"}, headers={"authorization": "Bearer b"}
    )
    assert response.status_code == 429


def test_auth_user_verify_invalid_json(client):
    response = client.post(
        "/auth/user/verify", content="invalid", headers={"authorization": "Bearer b"}
    )
    assert response.status_code == 400


def test_auth_user_verify_missing_code(client):
    response = client.post(
        "/auth/user/verify", json={}, headers={"authorization": "Bearer b"}
    )
    assert response.status_code == 400


def test_mcp_middleware_wrong_header_format(client, mock_deps):
    response = client.post("/mcp", headers={"authorization": "NotBearer token"})
    assert response.status_code == 403


def test_auth_user_verify_fail(client, mock_deps):
    mock_deps["auth"].complete_user_auth = AsyncMock(side_effect=ValueError("fail"))
    response = client.post(
        "/auth/user/verify", json={"code": "123"}, headers={"authorization": "Bearer b"}
    )
    assert response.status_code == 400
