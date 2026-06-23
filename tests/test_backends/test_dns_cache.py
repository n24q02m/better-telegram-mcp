import socket
from unittest.mock import patch

import pytest

from better_telegram_mcp.backends.bot_backend import BotBackend
from better_telegram_mcp.backends.security import (
    _DNS_CACHE,
    clear_dns_cache,
    validate_url,
)
from better_telegram_mcp.backends.user_backend import UserBackend
from better_telegram_mcp.config import Settings


def test_dns_cache_hits():
    clear_dns_cache()
    hostname = "example.com"
    safe_ip = "93.184.216.34"

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, 1, 6, "", (safe_ip, 80, 0, 0))]

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo) as mock_socket:
        # First call should hit the network
        res1 = validate_url(f"http://{hostname}/")
        assert res1 == safe_ip
        assert mock_socket.call_count == 1

        # Second call should hit the cache
        res2 = validate_url(f"http://{hostname}/")
        assert res2 == safe_ip
        assert mock_socket.call_count == 1


def test_dns_cache_expiration():
    clear_dns_cache()
    hostname = "expired.com"
    safe_ip = "1.2.3.4"

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, 1, 6, "", (safe_ip, 80, 0, 0))]

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo) as mock_socket:
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = 100.0

            # First call
            validate_url(f"http://{hostname}/")
            assert mock_socket.call_count == 1

            # Second call, still within TTL
            mock_time.return_value = 150.0
            validate_url(f"http://{hostname}/")
            assert mock_socket.call_count == 1

            # Third call, expired (TTL is 60.0)
            mock_time.return_value = 220.0
            validate_url(f"http://{hostname}/")
            assert mock_socket.call_count == 2


def test_clear_dns_cache():
    clear_dns_cache()
    hostname = "clear.com"
    safe_ip = "5.6.7.8"

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, 1, 6, "", (safe_ip, 80, 0, 0))]

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo) as mock_socket:
        validate_url(f"http://{hostname}/")
        assert mock_socket.call_count == 1

        clear_dns_cache()
        assert len(_DNS_CACHE) == 0

        validate_url(f"http://{hostname}/")
        assert mock_socket.call_count == 2


@pytest.mark.asyncio
async def test_backend_clear_cache_clears_dns():
    clear_dns_cache()
    hostname = "backend.com"
    safe_ip = "1.1.1.1"

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, 1, 6, "", (safe_ip, 80, 0, 0))]

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo) as mock_socket:
        validate_url(f"http://{hostname}/")
        assert mock_socket.call_count == 1

        # Test BotBackend
        bot = BotBackend("fake_token")
        await bot.clear_cache()
        assert len(_DNS_CACHE) == 0

        validate_url(f"http://{hostname}/")
        assert mock_socket.call_count == 2

        # Test UserBackend
        settings = Settings(api_id=123, api_hash="hash", phone="phone")
        user = UserBackend(settings)
        await user.clear_cache()
        assert len(_DNS_CACHE) == 0

        validate_url(f"http://{hostname}/")
        assert mock_socket.call_count == 3
