"""Tests for multi-user HTTP transport endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.http_multi_user import create_app


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def app(data_dir: Path):
    return create_app(
        data_dir=data_dir,
        public_url="https://test.example.com",
        dcr_secret="test-dcr-secret",
        api_id=12345,
        api_hash="test_api_hash",
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        """Health endpoint should return status ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["mode"] == "multi-user"
        assert "active_sessions" in body
        assert body["relay_enabled"] is False
        assert "timestamp" in body

    def test_health_reports_relay_enabled_without_leaking_url(
        self, data_dir: Path
    ) -> None:
        app = create_app(
            data_dir=data_dir,
            public_url="https://test.example.com",
            dcr_secret="test-dcr-secret",
            api_id=12345,
            api_hash="test_api_hash",
            relay_settings=Settings(relay_endpoint_url="https://example.com/events"),
        )
        client = TestClient(app)

        resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["relay_enabled"] is True
        assert "relay_endpoint_url" not in body
        assert "example.com" not in resp.text


class TestDCREndpoint:
    def test_register_success(self, client: TestClient) -> None:
        """Should register client and return credentials."""
        resp = client.post(
            "/auth/register",
            json={
                "redirect_uris": ["http://localhost/callback"],
                "client_name": "TestApp",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "client_id" in body
        assert "client_secret" in body
        assert body["client_name"] == "TestApp"
        assert body["redirect_uris"] == ["http://localhost/callback"]

    def test_register_deterministic(self, client: TestClient) -> None:
        """Same input should produce same credentials."""
        payload = {
            "redirect_uris": ["http://localhost/callback"],
            "client_name": "TestApp",
        }
        resp1 = client.post("/auth/register", json=payload)
        resp2 = client.post("/auth/register", json=payload)

        assert resp1.json()["client_id"] == resp2.json()["client_id"]
        assert resp1.json()["client_secret"] == resp2.json()["client_secret"]

    def test_register_invalid_json(self, client: TestClient) -> None:
        """Should return 400 for invalid JSON."""
        resp = client.post(
            "/auth/register",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400

    def test_register_invalid_uris_type(self, client: TestClient) -> None:
        """Should return 400 when redirect_uris is not a list."""
        resp = client.post(
            "/auth/register",
            json={"redirect_uris": "not-a-list"},
        )
        assert resp.status_code == 400

    def test_register_empty_body(self, client: TestClient) -> None:
        """Should accept empty body with defaults."""
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 201
        body = resp.json()
        assert body["redirect_uris"] == []
        assert body["client_name"] is None


class TestBotAuthEndpoint:
    def test_bot_auth_success(self, client: TestClient) -> None:
        """Should validate bot token and return bearer."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock()
            mock_instance.disconnect = AsyncMock()

            resp = client.post(
                "/auth/bot",
                json={"bot_token": "123456:ABC-DEF"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "bearer_token" in body
        assert body["token_type"] == "Bearer"
        assert body["mode"] == "bot"

    def test_bot_auth_invalid_token(self, client: TestClient) -> None:
        """Should return 401 for invalid bot token."""
        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.BotBackend"
        ) as MockBot:
            mock_instance = MockBot.return_value
            mock_instance.connect = AsyncMock(side_effect=Exception("Unauthorized"))
            mock_instance.disconnect = AsyncMock()

            resp = client.post(
                "/auth/bot",
                json={"bot_token": "invalid"},
            )

        assert resp.status_code == 401

    def test_bot_auth_missing_token(self, client: TestClient) -> None:
        """Should return 400 when bot_token is missing."""
        resp = client.post("/auth/bot", json={})
        assert resp.status_code == 400

    def test_bot_auth_empty_token(self, client: TestClient) -> None:
        """Should return 400 when bot_token is empty string."""
        resp = client.post("/auth/bot", json={"bot_token": ""})
        assert resp.status_code == 400


class TestUserAuthEndpoints:
    def test_send_code_success(self, client: TestClient) -> None:
        """Should send code and return bearer + phone_code_hash."""
        mock_telethon_client = MagicMock()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "hash123"
        mock_telethon_client.send_code_request = AsyncMock(return_value=mock_sent_code)

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            resp = client.post(
                "/auth/user/send-code",
                json={"phone": "+84912345678"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "bearer_token" in body
        assert body["phone_code_hash"] == "hash123"

    def test_send_code_missing_phone(self, client: TestClient) -> None:
        """Should return 400 when phone is missing."""
        resp = client.post("/auth/user/send-code", json={})
        assert resp.status_code == 400

    def test_verify_success(self, client: TestClient) -> None:
        """Should complete auth and return bearer + user info."""
        mock_telethon_client = MagicMock()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "hash123"
        mock_telethon_client.send_code_request = AsyncMock(return_value=mock_sent_code)

        mock_backend = MagicMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend._ensure_client = MagicMock(return_value=mock_telethon_client)
        mock_backend.sign_in = AsyncMock(
            return_value={
                "authenticated_as": "Test User",
                "username": "testuser",
            }
        )

        with patch(
            "better_telegram_mcp.auth.telegram_auth_provider.UserBackend",
            return_value=mock_backend,
        ):
            # Step 1: send code
            resp1 = client.post(
                "/auth/user/send-code",
                json={"phone": "+84912345678"},
            )
            bearer = resp1.json()["bearer_token"]

            # Step 2: verify
            resp2 = client.post(
                "/auth/user/verify",
                json={"code": "12345"},
                headers={"Authorization": f"Bearer {bearer}"},
            )

        assert resp2.status_code == 200
        body = resp2.json()
        assert body["bearer_token"] == bearer
        assert body["mode"] == "user"
        assert body["authenticated_as"] == "Test User"

    def test_verify_missing_bearer(self, client: TestClient) -> None:
        """Should return 401 when bearer is missing."""
        resp = client.post(
            "/auth/user/verify",
            json={"code": "12345"},
        )
        assert resp.status_code == 401

    def test_verify_missing_code(self, client: TestClient) -> None:
        """Should return 400 when code is missing."""
        resp = client.post(
            "/auth/user/verify",
            json={},
            headers={"Authorization": "Bearer some-token"},
        )
        assert resp.status_code == 400

    def test_verify_unknown_bearer(self, client: TestClient) -> None:
        """Should return 400 for unknown bearer token."""
        resp = client.post(
            "/auth/user/verify",
            json={"code": "12345"},
            headers={"Authorization": "Bearer unknown-bearer"},
        )
        assert resp.status_code == 400


class TestMCPEndpoint:
    def test_mcp_requires_bearer(self, client: TestClient) -> None:
        """Should return error when no bearer token."""
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
        )
        assert resp.status_code == 403

    def test_mcp_invalid_bearer(self, client: TestClient) -> None:
        """Should return error for invalid/expired bearer."""
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 403


class TestBackwardCompatibility:
    def test_stdio_mode_unchanged(self) -> None:
        """Server module-level _backend should still work in stdio mode."""
        from better_telegram_mcp import server

        # In non-multi-user mode, get_backend should raise if no backend
        server._multi_user_mode = False
        server._backend = None
        with pytest.raises(RuntimeError, match="Backend not initialized"):
            server.get_backend()

    def test_multi_user_mode_flag(self) -> None:
        """create_http_mcp_server should set _multi_user_mode flag."""
        from better_telegram_mcp.server import create_http_mcp_server

        mcp = create_http_mcp_server()
        assert mcp is not None

        from better_telegram_mcp import server

        assert server._multi_user_mode is True
        # Reset for other tests
        server._multi_user_mode = False

    def test_get_backend_prefers_context_var_in_multi_user(self) -> None:
        """In multi-user mode, get_backend should check ContextVar first."""
        from better_telegram_mcp import server
        from better_telegram_mcp.transports.http import _current_backend

        server._multi_user_mode = True
        server._backend = MagicMock()

        mock_ctx_backend = MagicMock()
        token = _current_backend.set(mock_ctx_backend)
        try:
            result = server.get_backend()
            assert result is mock_ctx_backend
        finally:
            _current_backend.reset(token)
            server._multi_user_mode = False
            server._backend = None

    def test_get_backend_falls_back_to_global_in_multi_user(self) -> None:
        """In multi-user mode with no ContextVar, falls back to global."""
        from better_telegram_mcp import server

        server._multi_user_mode = True
        mock_global = MagicMock()
        server._backend = mock_global
        try:
            result = server.get_backend()
            assert result is mock_global
        finally:
            server._multi_user_mode = False
            server._backend = None
