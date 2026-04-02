import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from better_telegram_mcp.auth_server import AuthServer

@pytest.fixture
def mock_backend():
    backend = AsyncMock()
    backend.is_authorized.return_value = False
    backend.sign_in.return_value = {"authenticated_as": "Test User"}
    backend.send_code.return_value = None
    return backend

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.phone = "+1234567890"
    return settings

def test_verify_rate_limiting(mock_backend, mock_settings):
    server = AuthServer(mock_backend, mock_settings)
    app = server._make_app()
    client = TestClient(app)

    # First 5 attempts should succeed
    for _ in range(5):
        response = client.post("/verify", json={"code": "12345"})
        assert response.status_code == 200
        assert response.json()["ok"] is True

    # 6th attempt should be rate limited
    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 429
    assert response.json()["ok"] is False
    assert "Too many attempts" in response.json()["error"]

def test_send_code_rate_limiting(mock_backend, mock_settings):
    server = AuthServer(mock_backend, mock_settings)
    app = server._make_app()
    client = TestClient(app)

    # First 5 attempts should succeed
    for _ in range(5):
        response = client.post("/send-code")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    # 6th attempt should be rate limited
    response = client.post("/send-code")
    assert response.status_code == 429
    assert response.json()["ok"] is False
    assert "Too many attempts" in response.json()["error"]
