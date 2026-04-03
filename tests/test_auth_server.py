from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from better_telegram_mcp.auth_server import (
    AuthServer,
    _find_free_port,
    _mask_phone,
    _sanitize_error,
)
from better_telegram_mcp.config import Settings


def test_find_free_port_success():
    port = _find_free_port()
    assert isinstance(port, int)
    assert port > 0


def test_find_free_port_fail():
    with patch("socket.socket") as mock_socket:
        mock_s = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_s
        mock_s.bind.side_effect = OSError("Address already in use")

        with pytest.raises(
            RuntimeError, match="Could not find a free port: Address already in use"
        ):
            _find_free_port()


def test_mask_phone():
    assert _mask_phone("1234567890") == "1234***7890"
    assert _mask_phone("1234567") == "12***"
    assert _mask_phone("12345678") == "1234***5678"
    assert _mask_phone("12") == "12***"


def test_sanitize_error():
    assert (
        _sanitize_error("phone code invalid (caused by SendCodeRequest)")
        == "Invalid OTP code. Please check and try again."
    )
    assert (
        _sanitize_error("password required")
        == "Two-factor authentication password is required."
    )
    assert _sanitize_error("Something else") == "Something else"
    assert (
        _sanitize_error("flood wait 300 seconds")
        == "Too many attempts. Please wait a moment and try again."
    )
    assert (
        _sanitize_error("password invalid")
        == "Incorrect 2FA password. Please try again."
    )
    assert (
        _sanitize_error("phone code expired")
        == "OTP code has expired. Please request a new one."
    )


def test_auth_server_init(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    assert server._settings.phone == "1234567890"
    assert server.port == 0


def test_auth_server_index(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "1234***7890" in response.text


@pytest.mark.asyncio
async def test_auth_server_status(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    mock_backend.is_authorized.return_value = True
    server._auth_name = "Test User"

    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "name": "Test User"}


@pytest.mark.asyncio
async def test_auth_server_status_unauthorized(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    mock_backend.is_authorized.return_value = False

    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


@pytest.mark.asyncio
async def test_auth_server_status_exception(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    mock_backend.is_authorized.side_effect = Exception("error")

    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


@pytest.mark.asyncio
async def test_auth_server_send_code_success(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    mock_backend.send_code.return_value = None

    response = client.post("/send-code")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_backend.send_code.assert_called_once_with("1234567890")


@pytest.mark.asyncio
async def test_auth_server_send_code_rate_limited(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    server._RATE_LIMIT_MAX = 0
    client = TestClient(server._make_app())

    response = client.post("/send-code")
    assert response.status_code == 429
    assert response.json()["ok"] is False


@pytest.mark.asyncio
async def test_auth_server_send_code_no_phone(mock_backend):
    settings = Settings()
    settings.phone = None
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    response = client.post("/send-code")
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "TELEGRAM_PHONE not configured" in response.json()["error"]


@pytest.mark.asyncio
async def test_auth_server_send_code_fail(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    mock_backend.send_code.side_effect = Exception("Some error")

    response = client.post("/send-code")
    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "Some error"}


@pytest.mark.asyncio
async def test_auth_server_verify_success(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    mock_backend.sign_in.return_value = {"authenticated_as": "Test User"}

    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "name": "Test User"}
    assert server._auth_complete.is_set()


@pytest.mark.asyncio
async def test_auth_server_verify_rate_limited(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    server._RATE_LIMIT_MAX = 0
    client = TestClient(server._make_app())

    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 429
    assert response.json()["ok"] is False


@pytest.mark.asyncio
async def test_auth_server_verify_no_phone(mock_backend):
    settings = Settings()
    settings.phone = None
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "TELEGRAM_PHONE not configured" in response.json()["error"]


@pytest.mark.asyncio
async def test_auth_server_verify_invalid_json(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    response = client.post("/verify", content="not json")
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "Invalid request" in response.json()["error"]


@pytest.mark.asyncio
async def test_auth_server_verify_no_code(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    response = client.post("/verify", json={})
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "Code is required" in response.json()["error"]


@pytest.mark.asyncio
async def test_auth_server_verify_needs_password(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    client = TestClient(server._make_app())

    mock_backend.sign_in.side_effect = Exception("2fa password needed")

    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["needs_password"] is True


@pytest.mark.asyncio
async def test_auth_server_lifecycle(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)

    with patch("uvicorn.Server.serve", new_callable=AsyncMock):
        url = await server.start()
        assert url.startswith("http://127.0.0.1:")
        assert server.port > 0
        assert server._uvicorn_server is not None

        # Stop
        await server.stop()
        assert server._uvicorn_server is None


@pytest.mark.asyncio
async def test_auth_server_wait_for_auth(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)

    server._auth_complete.set()
    await server.wait_for_auth()


def test_auth_server_rate_limiting(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)
    server._RATE_LIMIT_MAX = 2
    server._RATE_LIMIT_WINDOW = 60

    key = "test_key"
    assert server._check_rate_limit(key) is True
    assert server._check_rate_limit(key) is True
    assert server._check_rate_limit(key) is False


def test_get_client_ip(mock_backend):
    settings = Settings(phone="1234567890")
    server = AuthServer(mock_backend, settings)

    # Test Cloudflare header
    request = MagicMock()
    request.headers = {"cf-connecting-ip": "1.1.1.1"}
    assert server._get_client_ip(request) == "1.1.1.1"

    # Test X-Forwarded-For
    request.headers = {"x-forwarded-for": "2.2.2.2, 3.3.3.3"}
    assert server._get_client_ip(request) == "2.2.2.2"

    # Test fallback
    request.headers = {}
    request.client.host = "4.4.4.4"
    assert server._get_client_ip(request) == "4.4.4.4"
