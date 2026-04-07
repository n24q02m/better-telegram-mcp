"""Integration test for safe_download in security.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from better_telegram_mcp.backends.security import SecurityError, safe_download


@pytest.mark.asyncio
async def test_safe_download_success(tmp_path):
    url = "https://example.com/test.txt"
    dest = tmp_path / "downloaded.txt"

    # Mock httpx response
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200

    async def mock_aiter_bytes():
        yield b"hello world"

    mock_response.aiter_bytes = mock_aiter_bytes

    # Context manager mock
    class MockContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, *args):
            pass

    with patch(
        "better_telegram_mcp.backends.security.validate_url",
        return_value="93.184.216.34",
    ):
        with patch(
            "httpx.AsyncClient.stream", return_value=MockContext()
        ) as mock_stream:
            await safe_download(url, dest)

            assert dest.read_text() == "hello world"
            mock_stream.assert_called_once()
            args, kwargs = mock_stream.call_args
            assert args[1] == "https://93.184.216.34/test.txt"
            assert kwargs["headers"] == {"Host": "example.com"}
            assert kwargs["extensions"] == {"sni_hostname": "example.com"}


@pytest.mark.asyncio
async def test_safe_download_http_error(tmp_path):
    url = "https://example.com/test.txt"
    dest = tmp_path / "downloaded.txt"

    # Mock httpx response for failure
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 404

    class MockContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, *args):
            pass

    with patch(
        "better_telegram_mcp.backends.security.validate_url",
        return_value="93.184.216.34",
    ):
        with patch("httpx.AsyncClient.stream", return_value=MockContext()):
            with pytest.raises(SecurityError, match="Failed to download file: 404"):
                await safe_download(url, dest)
