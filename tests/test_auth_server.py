import asyncio
from unittest.mock import patch

import pytest

from better_telegram_mcp.auth_server import AuthServer
from better_telegram_mcp.config import Settings


@pytest.fixture
def settings():
    return Settings(api_id=123, api_hash="abc", phone="+1234567890")


@pytest.fixture
def auth_server(mock_backend, settings):
    return AuthServer(mock_backend, settings)


async def test_auth_server_start_success(auth_server):
    """Test successful server start."""
    with patch("uvicorn.Server") as mock_server_cls:
        mock_server = mock_server_cls.return_value

        # Make serve return a coroutine
        async def mock_serve():
            pass

        mock_server.serve.side_effect = mock_serve

        url = await auth_server.start()

        assert auth_server.port > 0
        assert url == f"http://127.0.0.1:{auth_server.port}"
        assert auth_server._uvicorn_server == mock_server
        mock_server.serve.assert_called_once()

        # Cleanup
        await auth_server.stop()
        assert auth_server._uvicorn_server is None


async def test_auth_server_start_oserror(auth_server, monkeypatch):
    """Test server start failure due to OSError (e.g. port busy)."""

    def mock_find_free_port():
        return 80

    monkeypatch.setattr(
        "better_telegram_mcp.auth_server._find_free_port", mock_find_free_port
    )

    with patch("uvicorn.Server") as mock_server_cls:
        # Mock Server creation to raise OSError
        mock_server_cls.side_effect = OSError("Address already in use")

        with pytest.raises(RuntimeError) as excinfo:
            await auth_server.start()

        assert "Could not start server on port 80" in str(excinfo.value)
        assert "Address already in use" in str(excinfo.value)


async def test_auth_server_stop_no_server(auth_server):
    """Test stopping when no server is running."""
    await auth_server.stop()
    assert auth_server._uvicorn_server is None


async def test_auth_server_wait_for_auth(auth_server):
    """Test wait_for_auth event."""
    wait_task = asyncio.create_task(auth_server.wait_for_auth())
    assert not wait_task.done()

    auth_server._auth_complete.set()
    await asyncio.sleep(0.1)
    assert wait_task.done()
