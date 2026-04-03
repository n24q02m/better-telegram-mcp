from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from better_telegram_mcp.auth_server import AuthServer
from better_telegram_mcp.config import Settings


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.is_authorized = AsyncMock(return_value=False)
    backend.send_code = AsyncMock()
    backend.sign_in = AsyncMock()
    return backend


@pytest.fixture
def settings():
    return Settings(phone="+1234567890", api_id=123, api_hash="abc")


@pytest.fixture
def client(mock_backend, settings):
    server = AuthServer(mock_backend, settings)
    app = server._make_app()
    return TestClient(app)


def test_verify_rate_limit_tracking(client, mock_backend):
    """Verifies that the new attempt-based rate limit works."""
    mock_backend.sign_in.side_effect = Exception("Invalid code")

    # Try 5 times (max allowed)
    for _ in range(5):
        response = client.post("/verify", json={"code": "12345"})
        assert response.status_code == 200
        assert response.json()["ok"] is False

    # 6th attempt should be rate limited (429)
    response = client.post("/verify", json={"code": "12345"})
    assert response.status_code == 429
    assert "Too many attempts" in response.json()["error"]


def test_verify_reset_on_success(client, mock_backend):
    """
    Verifies that the implementation resets on success.
    """
    # 4 failed attempts
    mock_backend.sign_in.side_effect = Exception("Invalid code")
    for _ in range(4):
        client.post("/verify", json={"code": "wrong"})

    # 5th attempt is successful
    mock_backend.sign_in.side_effect = None
    mock_backend.sign_in.return_value = {"authenticated_as": "Test User"}

    response = client.post("/verify", json={"code": "correct"})
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # 6th attempt should NOT be rate limited anymore because it was reset
    mock_backend.sign_in.side_effect = Exception("Invalid again")
    response = client.post("/verify", json={"code": "next"})

    # Now it should be 200 (but failing backend)
    assert response.status_code == 200
    assert response.json()["ok"] is False
