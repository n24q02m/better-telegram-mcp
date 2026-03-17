"""Input validation for security-sensitive operations."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse


class SecurityError(Exception):
    pass


# Private/internal IP ranges that should not be accessed via SSRF
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url(url: str) -> None:
    """Validate URL is safe (no SSRF to internal networks)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        msg = f"Only http/https URLs are allowed, got: {parsed.scheme}"
        raise SecurityError(msg)
    hostname = parsed.hostname
    if not hostname:
        msg = "URL has no hostname"
        raise SecurityError(msg)
    # Block metadata endpoints
    if hostname in ("metadata.google.internal", "metadata.internal"):
        msg = "Access to cloud metadata endpoints is blocked"
        raise SecurityError(msg)
    # Resolve and check IP
    try:
        addr = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if addr in network:
                msg = f"Access to internal/private IP {hostname} is blocked"
                raise SecurityError(msg)
    except ValueError:
        # Not an IP literal -- hostname resolution happens at fetch time
        # Block known dangerous hostnames
        if hostname in ("localhost", "0.0.0.0"):  # noqa: S104
            msg = f"Access to {hostname} is blocked"
            raise SecurityError(msg) from None
        # Try to resolve the hostname and check its IPs
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for info in addr_info:
                ip = info[4][0]
                try:
                    resolved_addr = ipaddress.ip_address(ip)
                    for network in _BLOCKED_NETWORKS:
                        if resolved_addr in network:
                            msg = f"Access to internal/private IP {ip} (resolved from {hostname}) is blocked"
                            raise SecurityError(msg)
                except ValueError:
                    pass
        except socket.gaierror:
            pass


def validate_file_path(file_path: str, *, allowed_dir: Path | None = None) -> Path:
    """Validate local file path is safe (no traversal to sensitive files)."""
    path = Path(file_path).resolve()
    # Block known sensitive paths
    _blocked_prefixes = (
        "/etc/",
        "/proc/",
        "/sys/",
        "/dev/",
        "/var/run/",
        "/var/log/",
        "/root/",
    )
    for prefix in _blocked_prefixes:
        if str(path).startswith(prefix):
            msg = f"Access to {prefix} is blocked for security"
            raise SecurityError(msg)
    # Block dotfiles in home directories (SSH keys, secrets, etc.)
    parts = path.parts
    for part in parts:
        if part.startswith(".") and part not in (".", ".."):
            msg = f"Access to hidden files/directories ({part}) is blocked"
            raise SecurityError(msg)
    # If an allowed_dir is specified, enforce containment
    if allowed_dir is not None:
        allowed = allowed_dir.resolve()
        if not str(path).startswith(str(allowed)):
            msg = f"Path must be within {allowed_dir}"
            raise SecurityError(msg)
    return path


def validate_output_dir(output_dir: str, *, base_dir: Path | None = None) -> Path:
    """Validate output directory is safe for writing."""
    path = Path(output_dir).resolve()
    # Block writing to system directories
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
    for prefix in _blocked_prefixes:
        if str(path).startswith(prefix):
            msg = f"Writing to {prefix} is blocked for security"
            raise SecurityError(msg)
    # Block hidden directories
    for part in path.parts:
        if part.startswith(".") and part not in (".", ".."):
            msg = f"Writing to hidden directories ({part}) is blocked"
            raise SecurityError(msg)
    if base_dir is not None:
        allowed = base_dir.resolve()
        if not str(path).startswith(str(allowed)):
            msg = f"Output path must be within {base_dir}"
            raise SecurityError(msg)
    return path
