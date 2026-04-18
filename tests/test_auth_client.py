from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from loguru import logger

from better_telegram_mcp.auth_client import AuthClient
from better_telegram_mcp.config import Settings


@pytest.fixture
def caplog_loguru(caplog):
    handler_id = logger.add(caplog.handler, format="{message}", level="INFO")
    yield caplog
    logger.remove(handler_id)


@pytest.mark.asyncio
async def test_create_session_does_not_log_url(caplog_loguru, caplog):
    # Mock settings and backend
    settings = Settings(phone="+1234567890", auth_url="https://example.com")
    backend = MagicMock()

    client = AuthClient(backend, settings)

    # Mock httpx response
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "url": "https://example.com/auth?token=secret_token",
        "token": "secret_token",
    }

    with patch.object(client._client, "post", AsyncMock(return_value=mock_resp)):
        url = await client.create_session()

    assert url == "https://example.com/auth?token=secret_token"

    # Check logs: "Auth session created" should be there, but NOT the URL
    assert "Auth session created" in caplog.text
    assert "https://example.com/auth?token=secret_token" not in caplog.text
    assert "secret_token" not in caplog.text
