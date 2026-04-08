from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from better_telegram_mcp.backends.bot_backend import BotBackend


@pytest.mark.asyncio
async def test_bot_send_media_url_ssrf_protection():
    """Verify BotBackend.send_media pins IP and downloads locally for URLs."""
    bot = BotBackend("token")

    # Mock validate_url to return a pinned IP
    pinned_ip = "93.184.216.34"
    with patch(
        "better_telegram_mcp.backends.bot_backend.validate_url", return_value=pinned_ip
    ) as mock_val:
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.content = b"fake data"
            mock_get.return_value.raise_for_status = lambda: None

            with patch.object(bot, "_call_form", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = {"ok": True}

                await bot.send_media(123, "photo", "https://example.com/image.jpg")

                # Verify validate_url was called with original URL
                mock_val.assert_called_with("https://example.com/image.jpg")

                # Verify httpx.get was called with pinned IP in URL but original host in headers/extensions
                args, kwargs = mock_get.call_args
                assert "https://93.184.216.34/image.jpg" in args
                assert kwargs["headers"]["Host"] == "example.com"
                assert kwargs["extensions"]["sni_hostname"] == "example.com"

                # Verify local file was used for upload
                call_args = mock_call.call_args
                files = call_args[1]["files"]
                assert "photo" in files
                filename, content = files["photo"]
                assert content == b"fake data"


@pytest.mark.asyncio
async def test_user_send_media_url_ssrf_protection(tmp_path):
    from better_telegram_mcp.backends.user_backend import UserBackend
    from better_telegram_mcp.config import Settings

    settings = Settings(api_id=123, api_hash="abc", phone="+123456", data_dir=tmp_path)
    backend = UserBackend(settings)
    backend._client = AsyncMock()
    backend._client.is_connected.return_value = True

    pinned_ip = "93.184.216.34"
    with patch(
        "better_telegram_mcp.backends.user_backend.validate_url", return_value=pinned_ip
    ) as mock_val:
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.content = b"user data"
            mock_get.return_value.raise_for_status = lambda: None

            backend._client.send_file = AsyncMock()

            await backend.send_media(123, "photo", "https://user-example.com/img.png")

            mock_val.assert_called_with("https://user-example.com/img.png")

            args, kwargs = mock_get.call_args
            assert "https://93.184.216.34/img.png" in args
            assert kwargs["headers"]["Host"] == "user-example.com"
            assert kwargs["extensions"]["sni_hostname"] == "user-example.com"

            # Verify Telethon send_file was called with a local path
            send_file_args = backend._client.send_file.call_args
            assert send_file_args[0][0] == 123
            local_path = send_file_args[0][1]
            assert Path(local_path).exists() is False  # Should be unlinked by finally
