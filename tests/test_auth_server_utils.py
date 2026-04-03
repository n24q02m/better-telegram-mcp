from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from better_telegram_mcp.auth_server import AuthServer, _mask_phone, _sanitize_error


@pytest.fixture
def mock_server():
    backend = AsyncMock()
    settings = MagicMock()
    settings.phone = "+1234567890"
    server = AuthServer(backend, settings)
    return server, backend, settings


class TestSanitizeError:
    def test_phone_number_invalid(self):
        assert _sanitize_error("PHONE_NUMBER_INVALID") == "Invalid phone number format"
        assert (
            _sanitize_error("The phone number is invalid")
            == "Invalid phone number format"
        )

    def test_password_required(self):
        assert _sanitize_error("password required") == (
            "Two-factor authentication password is required."
        )

    def test_password_invalid(self):
        assert _sanitize_error("The password is invalid") == (
            "Incorrect 2FA password. Please try again."
        )

    def test_phone_code_invalid(self):
        assert _sanitize_error("Phone code is invalid") == (
            "Invalid OTP code. Please check and try again."
        )

    def test_code_expired(self):
        assert _sanitize_error("Phone code has expired") == (
            "OTP code has expired. Please request a new one."
        )

    def test_flood_wait(self):
        assert _sanitize_error("Flood wait of 300 seconds") == (
            "Too many attempts. Please wait a moment and try again."
        )

    def test_caused_by_stripping(self):
        msg = "Some internal error (caused by AuthError)"
        assert _sanitize_error(msg) == "Some internal error"

    def test_unmapped_error(self):
        assert _sanitize_error("Something went wrong") == "Something went wrong"


class TestMaskPhone:
    def test_short_phone(self):
        assert _mask_phone("123") == "12***"
        assert _mask_phone("1234") == "12***"

    def test_medium_phone(self):
        # length 7
        assert _mask_phone("1234567") == "12***"

    def test_long_phone(self):
        assert _mask_phone("12345678") == "1234***5678"
        assert _mask_phone("+1234567890") == "+123***7890"


class TestAuthServerApp:
    def test_index_endpoint(self, mock_server):
        server, backend, settings = mock_server
        client = TestClient(server._make_app())
        response = client.get("/")
        assert response.status_code == 200
        assert "+123***7890" in response.text

    def test_index_endpoint_no_phone(self, mock_server):
        server, backend, settings = mock_server
        settings.phone = None
        client = TestClient(server._make_app())
        response = client.get("/")
        assert response.status_code == 200
        # "unknown" length 7 -> "un***"
        assert "un***" in response.text

    def test_status_endpoint_unauthorized(self, mock_server):
        server, backend, settings = mock_server
        backend.is_authorized.return_value = False
        client = TestClient(server._make_app())
        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False}

    def test_status_endpoint_authorized(self, mock_server):
        server, backend, settings = mock_server
        backend.is_authorized.return_value = True
        server._auth_name = "TestUser"
        client = TestClient(server._make_app())
        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "name": "TestUser"}

    def test_status_endpoint_error(self, mock_server):
        server, backend, settings = mock_server
        backend.is_authorized.side_effect = Exception("Boom")
        client = TestClient(server._make_app())
        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False}

    def test_send_code_success(self, mock_server):
        server, backend, settings = mock_server
        backend.send_code.return_value = None
        client = TestClient(server._make_app())
        response = client.post("/send-code")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        backend.send_code.assert_awaited_once_with("+1234567890")

    def test_send_code_no_phone(self, mock_server):
        server, backend, settings = mock_server
        settings.phone = None
        client = TestClient(server._make_app())
        response = client.post("/send-code")
        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "not configured" in response.json()["error"]

    def test_send_code_error(self, mock_server):
        server, backend, settings = mock_server
        backend.send_code.side_effect = Exception("PHONE_NUMBER_INVALID")
        client = TestClient(server._make_app())
        response = client.post("/send-code")
        assert response.status_code == 200
        assert response.json() == {"ok": False, "error": "Invalid phone number format"}

    def test_verify_success(self, mock_server):
        server, backend, settings = mock_server
        backend.sign_in.return_value = {"authenticated_as": "TestUser"}
        client = TestClient(server._make_app())
        response = client.post("/verify", json={"code": "12345"})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "name": "TestUser"}
        assert server._auth_complete.is_set()

    def test_verify_no_code(self, mock_server):
        server, backend, settings = mock_server
        client = TestClient(server._make_app())
        response = client.post("/verify", json={})
        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "Code is required" in response.json()["error"]

    def test_verify_invalid_json(self, mock_server):
        server, backend, settings = mock_server
        client = TestClient(server._make_app())
        response = client.post("/verify", content="invalid json")
        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "Invalid request" in response.json()["error"]

    def test_verify_no_phone(self, mock_server):
        server, backend, settings = mock_server
        settings.phone = None
        client = TestClient(server._make_app())
        response = client.post("/verify", json={"code": "12345"})
        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "not configured" in response.json()["error"]

    def test_verify_needs_password(self, mock_server):
        server, backend, settings = mock_server
        backend.sign_in.side_effect = Exception("password required")
        client = TestClient(server._make_app())
        response = client.post("/verify", json={"code": "12345"})
        assert response.status_code == 200
        assert response.json()["needs_password"] is True
        assert (
            "Two-factor authentication password is required" in response.json()["error"]
        )

    def test_rate_limit(self, mock_server):
        server, backend, settings = mock_server
        backend.send_code.return_value = None
        backend.sign_in.return_value = {"authenticated_as": "TestUser"}
        client = TestClient(server._make_app())
        for _ in range(5):
            client.post("/send-code")
        response = client.post("/send-code")
        assert response.status_code == 429
        assert "Too many attempts" in response.json()["error"]

        for _ in range(5):
            client.post("/verify", json={"code": "12345"})
        response = client.post("/verify", json={"code": "12345"})
        assert response.status_code == 429
        assert "Too many attempts" in response.json()["error"]

    def test_client_ip_headers(self, mock_server):
        server, backend, settings = mock_server
        backend.send_code.return_value = None
        app = server._make_app()
        client = TestClient(app)

        response = client.post("/send-code", headers={"cf-connecting-ip": "1.1.1.1"})
        assert response.status_code == 200
        assert "send_code:1.1.1.1" in server._rate_limits

        server._rate_limits.clear()
        response = client.post(
            "/send-code", headers={"x-forwarded-for": "2.2.2.2, 3.3.3.3"}
        )
        assert response.status_code == 200
        assert "send_code:2.2.2.2" in server._rate_limits


class TestAuthServerStartStop:
    @pytest.mark.asyncio
    async def test_find_free_port(self):
        from better_telegram_mcp.auth_server import _find_free_port

        port = _find_free_port()
        assert isinstance(port, int)
        assert port > 0

    @pytest.mark.asyncio
    async def test_start_stop(self, mock_server):
        server, backend, settings = mock_server
        with patch("uvicorn.Server.serve", new_callable=AsyncMock):
            url = await server.start()
            assert "127.0.0.1" in url
            assert server.port > 0
            await server.stop()
            assert server._uvicorn_server is None

    @pytest.mark.asyncio
    async def test_wait_for_auth(self, mock_server):
        server, backend, settings = mock_server
        server._auth_complete.set()
        await server.wait_for_auth()
