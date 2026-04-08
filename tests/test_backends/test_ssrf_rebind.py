import ipaddress
import socket
from urllib.parse import urlparse

import pytest

from better_telegram_mcp.backends.security import SecurityError, validate_url


def test_validate_url_returns_ip(monkeypatch):
    """Test that validate_url returns the resolved IP address."""

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

    ip = validate_url("https://example.com")
    assert ip == "93.184.216.34"
    ipaddress.ip_address(ip)


def test_dns_rebinding_simulation(monkeypatch):
    """
    Simulate DNS rebinding where the first resolution is safe,
    but the caller is forced to use the returned IP, preventing the rebind.
    """
    # 1. Host resolves to public IP initially
    public_ip = "93.184.216.34"

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (public_ip, 443))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

    # Validation passes and returns the public IP
    pinned_ip = validate_url("https://malicious.com")
    assert pinned_ip == public_ip

    # 2. Now simulate DNS rebind where hostname would resolve to local IP
    local_ip = "127.0.0.1"

    def mock_getaddrinfo_rebind(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (local_ip, 443))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo_rebind)

    # Even if resolution now returns local_ip, the application uses pinned_ip
    assert pinned_ip == public_ip


def test_validate_url_blocks_rebinding_during_validation(monkeypatch):
    """
    If a hostname resolves to multiple IPs, one of which is private, it should be blocked.
    """

    def mock_getaddrinfo_multi(host, port, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo_multi)

    with pytest.raises(SecurityError, match="internal/private IP"):
        validate_url("https://mixed-results.com")


def test_validate_url_with_port(monkeypatch):
    """Verify that port is preserved when pinning IP."""

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 8080))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

    url = "http://example.com:8080/path"
    pinned_ip = validate_url(url)
    parsed = urlparse(url)
    netloc = pinned_ip
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    pinned_url = parsed._replace(netloc=netloc).geturl()

    assert pinned_url == "http://93.184.216.34:8080/path"
