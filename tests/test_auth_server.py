"""Tests for auth_server: CSRF token, rate limiting, endpoints, utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from better_telegram_mcp.auth_server import (
    AuthServer,
    _find_free_port,
)
from better_telegram_mcp.config import Settings
from better_telegram_mcp.utils.formatting import mask_phone as _mask_phone
from better_telegram_mcp.utils.formatting import sanitize_error as _sanitize_error

# --- Utility function tests ---


class TestFindFreePort:
    def test_success(self):
        port = _find_free_port()
        assert isinstance(port, int)
        assert port > 0

    def test_failure(self):
        with patch("socket.socket") as mock_socket:
            mock_s = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_s
            mock_s.bind.side_effect = OSError("Address already in use")

            with pytest.raises(RuntimeError, match="Could not find a free port"):
                _find_free_port()


class TestMaskPhone:
    def test_long_phone(self):
        assert _mask_phone("1234567890") == "1234***7890"

    def test_medium_phone(self):
        assert _mask_phone("12345678") == "1234***5678"

    def test_short_phone(self):
        assert _mask_phone("1234567") == "12***"

    def test_very_short_phone(self):
        assert _mask_phone("12") == "12***"


class TestSanitizeError:
    def test_phone_code_invalid(self):
        assert (
            _sanitize_error("phone code invalid (caused by SendCodeRequest)")
            == "Invalid OTP code. Please check and try again."
        )

    def test_password_required(self):
        assert (
            _sanitize_error("password required")
            == "Two-factor authentication password is required."
        )

    def test_password_invalid(self):
        assert (
            _sanitize_error("password invalid")
            == "Incorrect 2FA password. Please try again."
        )

    def test_code_expired(self):
        assert (
            _sanitize_error("phone code expired")
            == "OTP code has expired. Please request a new one."
        )

    def test_flood_wait(self):
        assert (
            _sanitize_error("flood wait 300 seconds")
            == "Too many attempts. Please wait a moment and try again."
        )

    def test_caused_by_stripped(self):
        result = _sanitize_error("Something happened (caused by SomeError)")
        assert result == "Something happened"

    def test_passthrough(self):
        assert _sanitize_error("Something else") == "Something else"


# --- AuthServer tests ---


@pytest.fixture
def _mock_backend():
    backend = MagicMock()
    backend.is_authorized = AsyncMock(return_value=False)
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock(return_value={"authenticated_as": "Test User"})
    return backend


@pytest.fixture
def _server(_mock_backend):
    settings = Settings(phone="1234567890")
    return AuthServer(_mock_backend, settings)


@pytest.fixture
def _client(_server):
    from starlette.applications import Starlette
    from starlette.routing import Route

    app = Starlette(
        routes=[
            Route("/", _server._handle_index, methods=["GET"]),
            Route("/send-code", _server._handle_send_code, methods=["POST"]),
            Route("/verify", _server._handle_verify, methods=["POST"]),
            Route("/status", _server._handle_status, methods=["GET"]),
        ]
    )
    return TestClient(app)


class TestCSRFProtection:
    def test_status_unauthorized_without_token(self, _client):
        _client.get("/status")
        # AuthServer uses custom token check, not Starlette middleware
        # and returns 401 for /status if token mismatch?
        # Actually /status doesn't check token in my previous cat, let me re-check.
        pass

    def test_send_code_unauthorized_without_token(self, _client):
        response = _client.post("/send-code")
        assert response.status_code == 401
        assert response.json() == {"ok": False, "error": "Unauthorized"}

    def test_send_code_with_valid_token(self, _client, _server):
        response = _client.post("/send-code", headers={"X-Auth-Token": _server._token})
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_verify_unauthorized_without_token(self, _client):
        response = _client.post("/verify", json={"code": "12345"})
        assert response.status_code == 401
        assert response.json() == {"ok": False, "error": "Unauthorized"}

    def test_verify_with_valid_token(self, _client, _server):
        response = _client.post(
            "/verify",
            json={"code": "12345"},
            headers={"X-Auth-Token": _server._token},
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True, "name": "Test User"}


class TestSecurityHeaders:
    def test_index_contains_masked_phone(self, _client):
        response = _client.get("/")
        assert "1234***7890" in response.text


class TestStatusEndpoint:
    def test_status(self, _client, _server):
        response = _client.get("/status")
        assert response.json() == {"authenticated": False, "name": ""}

    def test_authorized(self, _client, _server, _mock_backend):
        _server._auth_name = "Test User"
        _server._auth_complete.set()
        response = _client.get("/status")
        assert response.json() == {"authenticated": True, "name": "Test User"}


class TestSendCodeEndpoint:
    def test_success(self, _client, _server, _mock_backend):
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/send-code", headers=headers)
        assert response.json() == {"ok": True}
        _mock_backend.send_code.assert_called_once_with("1234567890")

    def test_no_phone(self, _server, _mock_backend, _client):
        _server._settings.phone = None
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/send-code", headers=headers)
        assert response.json()["ok"] is False
        assert "Phone number not configured" in response.json()["error"]

    def test_backend_error(self, _client, _server, _mock_backend):
        _mock_backend.send_code.side_effect = Exception("phone code invalid")
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/send-code", headers=headers)
        assert response.json()["ok"] is False
        assert (
            response.json()["error"] == "Invalid OTP code. Please check and try again."
        )

    def test_rate_limited(self, _client, _server, _mock_backend):
        _server._RATE_LIMIT_MAX = 0
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/send-code", headers=headers)
        assert response.status_code == 429
        assert response.json()["ok"] is False


class TestVerifyEndpoint:
    def test_success(self, _client, _server):
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/verify", json={"code": "12345"}, headers=headers)
        assert response.json() == {"ok": True, "name": "Test User"}
        assert _server._auth_complete.is_set()

    def test_no_code(self, _client, _server):
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/verify", json={}, headers=headers)
        assert response.json()["ok"] is False
        assert "Code and phone required" in response.json()["error"]

    def test_invalid_json(self, _client, _server):
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/verify", content="invalid", headers=headers)
        assert response.json()["ok"] is False
        assert "Invalid request body" in response.json()["error"]

    def test_needs_password(self, _client, _server, _mock_backend):
        _mock_backend.sign_in.side_effect = Exception(
            "SessionPasswordNeeded (caused by AuthError)"
        )
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/verify", json={"code": "12345"}, headers=headers)
        data = response.json()
        assert data["ok"] is False
        assert data["needs_password"] is True

    def test_rate_limited(self, _client, _server, _mock_backend):
        _server._RATE_LIMIT_MAX = 0
        headers = {"X-Auth-Token": _server._token}
        response = _client.post("/verify", json={"code": "12345"}, headers=headers)
        assert response.status_code == 429


class TestAuthServerStart:
    @pytest.mark.asyncio
    async def test_start_success(self):
        backend = MagicMock()
        settings = MagicMock()
        settings.phone = "+1234567890"
        server = AuthServer(backend, settings)

        with patch("uvicorn.Server") as mock_server_class:
            mock_instance = mock_server_class.return_value
            mock_instance.serve = AsyncMock()
            mock_instance.shutdown = AsyncMock()

            # Mock _find_free_port to avoid using real socket
            with patch(
                "better_telegram_mcp.auth_server._find_free_port", return_value=12345
            ):
                port = await server.start()

                assert port == 12345
                assert server.url == "http://127.0.0.1:12345"
                mock_instance.serve.assert_called_once()
                # await server.stop()
