import pytest
import time
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from better_telegram_mcp.auth_server import AuthServer
from better_telegram_mcp.config import Settings

@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.is_authorized = AsyncMock(return_value=False)
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock(side_effect=Exception("Invalid code"))
    return backend

@pytest.fixture
def settings():
    s = Settings()
    s.phone = "+1234567890"
    return s

def test_verify_rate_limit(mock_backend, settings):
    server = AuthServer(mock_backend, settings)
    # Speed up cooldown for testing
    server.MAX_VERIFY_ATTEMPTS = 3
    server.VERIFY_COOLDOWN_SECONDS = 2

    app = server._make_app()
    client = TestClient(app)

    # First 3 attempts should fail with "Invalid OTP code"
    for _ in range(3):
        response = client.post("/verify", json={"code": "12345"})
        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "Invalid OTP code" in response.json()["error"]

    # 4th attempt should be rate limited (429)
    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 429
    assert "Too many attempts" in response.json()["error"]

    # Wait for cooldown
    time.sleep(2.1)

    # After cooldown, should be able to try again
    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "Invalid OTP code" in response.json()["error"]

def test_verify_reset_on_success(mock_backend, settings):
    server = AuthServer(mock_backend, settings)
    server.MAX_VERIFY_ATTEMPTS = 3

    app = server._make_app()
    client = TestClient(app)

    # 2 failures
    for _ in range(2):
        client.post("/verify", json={"code": "wrong"})

    assert server._verify_attempts == 2

    # 1 success
    mock_backend.sign_in = AsyncMock(return_value={"authenticated_as": "User"})
    response = client.post("/verify", json={"code": "correct"})
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # Reset to 0
    assert server._verify_attempts == 0
