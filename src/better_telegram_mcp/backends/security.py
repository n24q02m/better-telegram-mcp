"""Input validation for security-sensitive operations."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse


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
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::ffff:0:0/96"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def validate_url(url: str) -> None:
    """Validate URL is safe (no SSRF to internal networks)."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        msg = f"Only http/https URLs are allowed, got: {parsed.scheme}"
        raise SecurityError(msg)
    hostname = parsed.hostname
    if not hostname:
        msg = "URL has no hostname"
        raise SecurityError(msg)
    # Block metadata endpoints
    if hostname in {"metadata.google.internal", "metadata.internal"}:
        msg = "Access to cloud metadata endpoints is blocked"
        raise SecurityError(msg)
    # Resolve and check IPs
    # Not an IP literal -- resolve to prevent SSRF via DNS like 127.0.0.1.nip.io
    # Block known dangerous hostnames as an early check
    if hostname in {"localhost", "0.0.0.0"}:  # noqa: S104
        msg = f"Access to {hostname} is blocked"
        raise SecurityError(msg)
    try:
        # Get all IPs for this hostname
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            addr = ipaddress.ip_address(ip_str)
            for network in _BLOCKED_NETWORKS:
                if addr in network:
                    msg = f"Access to internal/private IP {ip_str} ({hostname}) is blocked"
                    raise SecurityError(msg)
    except OSError as e:
        # If hostname resolution fails, deny access instead of silently passing
        # to prevent bypassing SSRF checks via transient failures or DNS rebinding
        msg = f"Failed to resolve hostname {hostname}"
        raise SecurityError(msg) from e


def validate_file_path(file_path: str, *, allowed_dir: Path | None = None) -> Path:
    """Validate local file path is safe (no traversal to sensitive files)."""
    # Sentinel: Expand user (`~`) before resolving to prevent TOCTOU bypasses where
    # `~` is treated as a literal local directory `~/...` during validation but expanded
    # by downstream APIs to the actual home directory `/home/user/...`.
    raw_path = Path(file_path).expanduser()
    path = raw_path.resolve()

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

    # 1. Lexical check (pre-resolve) for defense-in-depth
    lexical_str = raw_path.as_posix()
    lexical_check = lexical_str if lexical_str.endswith("/") else lexical_str + "/"

    for prefix in _blocked_prefixes:
        # Check lexical path
        if lexical_check.startswith(prefix):
            msg = f"Access to {prefix} is blocked for security"
            raise SecurityError(msg)

        # 2. Canonical check (post-resolve)
        # Check resolved path against both literal prefix and canonical prefix.
        # This handles macOS firmlinks and complex symlinks.
        try:
            # Resolve prefix to its real location (e.g. /etc -> /private/etc on macOS)
            canonical_prefix = Path(prefix).resolve()
            if path.is_relative_to(canonical_prefix):
                msg = f"Access to {prefix} is blocked for security"
                raise SecurityError(msg)
        except (OSError, RuntimeError):
            pass

        # Fallback: simple prefix match on resolved path if is_relative_to didn't catch it
        # or if resolution failed.
        resolved_str = path.as_posix()
        resolved_check = (
            resolved_str if resolved_str.endswith("/") else resolved_str + "/"
        )
        if resolved_check.startswith(prefix):
            msg = f"Access to {prefix} is blocked for security"
            raise SecurityError(msg)

    # Block dotfiles in home directories (SSH keys, secrets, etc.)
    parts = path.parts
    for part in parts:
        if part.startswith(".") and part not in {".", ".."}:
            msg = f"Access to hidden files/directories ({part}) is blocked"
            raise SecurityError(msg)

    # If an allowed_dir is specified, enforce containment
    if allowed_dir is not None:
        allowed = allowed_dir.resolve()
        if not path.is_relative_to(allowed):
            msg = f"Path must be within {allowed_dir}"
            raise SecurityError(msg)
    return path


def validate_output_dir(output_dir: str, *, base_dir: Path | None = None) -> Path:
    """Validate output directory is safe for writing."""
    # Sentinel: Expand user (`~`) before resolving to prevent TOCTOU bypasses where
    # `~` is treated as a literal local directory `~/...` during validation but expanded
    # by downstream APIs to the actual home directory `/home/user/...`.
    raw_path = Path(output_dir).expanduser()
    path = raw_path.resolve()

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

    # 1. Lexical check (pre-resolve) for defense-in-depth
    lexical_str = raw_path.as_posix()
    lexical_check = lexical_str if lexical_str.endswith("/") else lexical_str + "/"

    for prefix in _blocked_prefixes:
        # Check lexical path
        if lexical_check.startswith(prefix):
            msg = f"Writing to {prefix} is blocked for security"
            raise SecurityError(msg)

        # 2. Canonical check (post-resolve)
        try:
            canonical_prefix = Path(prefix).resolve()
            if path.is_relative_to(canonical_prefix):
                msg = f"Writing to {prefix} is blocked for security"
                raise SecurityError(msg)
        except (OSError, RuntimeError):
            pass

        # Fallback
        resolved_str = path.as_posix()
        resolved_check = (
            resolved_str if resolved_str.endswith("/") else resolved_str + "/"
        )
        if resolved_check.startswith(prefix):
            msg = f"Writing to {prefix} is blocked for security"
            raise SecurityError(msg)

    # Block hidden directories
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
