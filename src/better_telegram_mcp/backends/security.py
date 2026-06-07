"""Input validation for security-sensitive operations."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpcore


class SecurityError(Exception):
    pass


# Private/internal IP ranges that should not be accessed via SSRF
_BLOCKED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # Documentation (TEST-NET-1)
    ipaddress.ip_network("198.18.0.0/15"),  # Network Interconnect Device Benchmark Testing
    ipaddress.ip_network("198.51.100.0/24"),  # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),  # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::/128"),  # Unspecified address
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped addresses
    ipaddress.ip_network("100::/64"),  # Discard-Only Address Block
    ipaddress.ip_network("2001:db8::/32"),  # Documentation
    ipaddress.ip_network("fc00::/7"),  # Unique Local Address
    ipaddress.ip_network("fe80::/10"),  # Link-Local Address
    ipaddress.ip_network("ff00::/8"),  # Multicast
)


def _validate_ip(ip_str: str, hostname: str | None = None) -> None:
    """Validate that an IP address is not in a blocked network."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        # Not an IP address, skip validation
        return

    # Handle IPv4-mapped IPv6 addresses (::ffff:127.0.0.1)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped

    for network in _BLOCKED_NETWORKS:
        if addr in network:
            context = f" ({hostname})" if hostname else ""
            msg = f"Access to internal/private IP {ip_str}{context} is blocked"
            raise SecurityError(msg)


class SSRFProtectedNetworkBackend(httpcore.AnyIOBackend):
    """Network backend that prevents SSRF by pinning hostnames to safe IPs."""

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> httpcore.AsyncNetworkStream:
        """Resolve host, validate all IPs, and connect to the first safe one."""
        try:
            # Resolve the hostname once
            # Use asyncio.to_thread for blocking getaddrinfo
            addr_info = await asyncio.to_thread(
                socket.getaddrinfo, host, port, family=socket.AF_UNSPEC
            )
        except socket.gaierror as e:
            msg = f"Failed to resolve hostname {host}"
            raise SecurityError(msg) from e

        if not addr_info:
            msg = f"Failed to resolve hostname {host}"
            raise SecurityError(msg)

        # Validate all resolved IPs
        for item in addr_info:
            sockaddr = item[4]
            ip = sockaddr[0]
            _validate_ip(ip, host)

        # Pin to the first safe IP by replacing the 'host' with the IP
        # This prevents DNS rebinding because httpcore will use this IP for the connection
        # and won't re-resolve it.
        safe_ip = addr_info[0][4][0]

        return await super().connect_tcp(
            safe_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Any = None,
    ) -> httpcore.AsyncNetworkStream:
        """Block Unix socket connections to prevent local service access."""
        msg = "Unix socket connections are blocked for security"
        raise SecurityError(msg)


def validate_url(url: str) -> None:
    """Validate URL scheme and hostname are allowed."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        msg = f"Only http/https URLs are allowed, got: {parsed.scheme}"
        raise SecurityError(msg)

    hostname = parsed.hostname
    if not hostname:
        msg = "URL has no hostname"
        raise SecurityError(msg)

    # Block metadata endpoints by name
    if hostname.lower() in {
        "metadata.google.internal",
        "metadata.internal",
        "169.254.169.254",
        "instance-data",
    }:
        msg = "Access to cloud metadata endpoints is blocked"
        raise SecurityError(msg)

    # Early check for common dangerous hostnames
    if hostname.lower() in {"localhost", "0.0.0.0"}:  # noqa: S104
        msg = f"Access to {hostname} is blocked"
        raise SecurityError(msg)

    # Check if hostname is a literal IP and block early
    _validate_ip(hostname, hostname)


def _normalize_for_prefix_check(path: Path) -> str:
    """Return a forward-slash path string suitable for blocked-prefix matching."""
    path_str = str(path).replace("\\", "/")
    if path_str.startswith("/private/"):
        path_str = path_str[len("/private") :]
    return path_str if path_str.endswith("/") else path_str + "/"


def _is_under_blocked_prefix(
    resolved: Path, lexical: Path, prefixes: tuple[str, ...]
) -> str | None:
    """Return the blocked prefix that ``resolved``/``lexical`` falls under, else None."""
    candidates = {resolved, lexical}
    for prefix in prefixes:
        prefix_dir = Path(prefix.rstrip("/"))
        blocked_dirs = {prefix_dir}
        try:
            blocked_dirs.add(prefix_dir.resolve())
        except OSError:
            pass
        for candidate in candidates:
            for blocked in blocked_dirs:
                if candidate == blocked or candidate.is_relative_to(blocked):
                    return prefix
    return None


def validate_file_path(file_path: str, *, allowed_dir: Path | None = None) -> Path:
    """Validate local file path is safe (no traversal to sensitive files)."""
    path = Path(file_path).expanduser().resolve()
    _blocked_prefixes = (
        "/etc/",
        "/proc/",
        "/sys/",
        "/dev/",
        "/var/run/",
        "/var/log/",
        "/root/",
    )
    lexical = Path(file_path).expanduser()
    blocked = _is_under_blocked_prefix(path, lexical, _blocked_prefixes)
    if blocked is not None:
        msg = f"Access to {blocked} is blocked for security"
        raise SecurityError(msg)
    for part in path.parts:
        if part.startswith(".") and part not in {".", ".."}:
            msg = f"Access to hidden files/directories ({part}) is blocked"
            raise SecurityError(msg)
    if allowed_dir is not None:
        allowed = allowed_dir.resolve()
        if not path.is_relative_to(allowed):
            msg = f"Path must be within {allowed_dir}"
            raise SecurityError(msg)
    return path


def validate_output_dir(output_dir: str, *, base_dir: Path | None = None) -> Path:
    """Validate output directory is safe for writing."""
    path = Path(output_dir).expanduser().resolve()
    _blocked_prefixes = (
        "/etc/",
        "/proc/",
        "/sys/",
        "/dev/",
        "/var/run/",
        "/var/log/",
        "/var/spool/",
        "/root/",
        "/usr/",
        "/bin/",
        "/sbin/",
        "/boot/",
        "/lib/",
    )
    lexical = Path(output_dir).expanduser()
    blocked = _is_under_blocked_prefix(path, lexical, _blocked_prefixes)
    if blocked is not None:
        msg = f"Writing to {blocked} is blocked for security"
        raise SecurityError(msg)
    for part in path.parts:
        if part.startswith(".") and part not in {".", ".."}:
            msg = f"Writing to hidden directories ({part}) is blocked"
            raise SecurityError(msg)
    if base_dir is not None:
        allowed = base_dir.resolve()
        if not path.is_relative_to(allowed):
            msg = f"Output path must be within {base_dir}"
            raise SecurityError(msg)
    return path


async def fetch_url_safely(url: str, timeout: float = 30.0) -> bytes:
    """Fetch URL content safely using an SSRF-protected backend."""
    import httpx

    validate_url(url)

    # Use the custom backend to pin hostnames to safe IPs and prevent DNS rebinding.
    pool = httpcore.AsyncConnectionPool(
        network_backend=SSRFProtectedNetworkBackend(),
    )
    transport = httpx.AsyncHTTPTransport()
    transport._pool = pool  # Inject our custom pool

    async with httpx.AsyncClient(transport=transport, verify=True) as client:
        # We can safely follow redirects because the backend validates every
        # new connection's IP address.
        resp = await client.get(
            url,
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content
