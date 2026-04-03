from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from better_telegram_mcp.auth_server import AuthServer


@pytest.mark.asyncio
async def test_auth_server_start_os_error():
    """Test that AuthServer.start raises RuntimeError on OSError (e.g., port in use)."""
    backend = MagicMock()
    settings = MagicMock()
    settings.phone = "+1234567890"

    server = AuthServer(backend, settings)

    # Mock uvicorn.Server to raise OSError during serve
    with patch("uvicorn.Server") as mock_server_class:
        mock_instance = mock_server_class.return_value
        # uvicorn.Server.serve is an async method
        mock_instance.serve = AsyncMock(side_effect=OSError("Address already in use"))

        with pytest.raises(RuntimeError) as excinfo:
            await server.start()

        assert "Could not start server on port" in str(excinfo.value)
        assert "Address already in use" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, OSError)


@pytest.mark.asyncio
async def test_auth_server_start_success():
    """Test that AuthServer.start starts successfully when no error occurs."""
    backend = MagicMock()
    settings = MagicMock()
    settings.phone = "+1234567890"

    server = AuthServer(backend, settings)

    with patch("uvicorn.Server") as mock_server_class:
        mock_instance = mock_server_class.return_value
        mock_instance.serve = AsyncMock()

        url = await server.start()

        assert url.startswith("http://127.0.0.1:")
        assert server.port > 0
        mock_instance.serve.assert_called_once()
        await server.stop()
