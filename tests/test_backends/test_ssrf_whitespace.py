from unittest.mock import AsyncMock, patch

import pytest

from better_telegram_mcp.backends.bot_backend import BotBackend
from better_telegram_mcp.backends.user_backend import UserBackend


@pytest.mark.asyncio
async def test_bot_backend_ssrf_whitespace_url():
    backend = BotBackend("12345:ABCDEF")
    with patch(
        "better_telegram_mcp.backends.bot_backend.fetch_url_safely",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = b"test"

        backend._call_form = AsyncMock()
        await backend.send_media(123, "photo", "   http://127.0.0.1")

        mock_fetch.assert_called_once_with("http://127.0.0.1")


@pytest.mark.asyncio
async def test_user_backend_ssrf_whitespace_url():
    backend = UserBackend({})
    backend._client = AsyncMock()
    backend._connected = True
    with patch(
        "better_telegram_mcp.backends.user_backend.fetch_url_safely",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = b"test"

        backend._serialize_message = lambda x: {}
        await backend.send_media(123, "photo", "   http://127.0.0.1")

        mock_fetch.assert_called_once_with("http://127.0.0.1")
