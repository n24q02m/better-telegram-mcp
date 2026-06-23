"""Input validation for security-sensitive operations."""

from __future__ import annotations

import asyncio
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
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network(
        "198.18.0.0/15"
    ),  # Network Interconnect Device Benchmark Testing
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Limited Broadcast
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::ffff:0:0/96"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("2001:db8::/32"),  # Documentation
    ipaddress.ip_network("3ffe::/16"),  # 6bone (deprecated)
    ipaddress.ip_network("ff00::/8"),  # Multicast
)


def _validate_ip(ip_str: str, hostname: str) -> None:
    """Validate an IP address against blocked networks. Handles IPv4-mapped IPv6."""
    try:
        addr = ipaddress.ip_address(ip_str)
        # Handle IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
        if addr.version == 6 and addr.ipv4_mapped:
            addr = addr.ipv4_mapped

        for network in _BLOCKED_NETWORKS:
            if addr in network:
                msg = f"Access to internal/private IP {ip_str} ({hostname}) is blocked"
                raise SecurityError(msg)
    except ValueError as e:
        # Handle potential zone indices in IPv6 (e.g., fe80::1%eth0)
        if "%" in ip_str:
            try:
                clean_ip = ip_str.split("%")[0]
                addr = ipaddress.ip_address(clean_ip)
                for network in _BLOCKED_NETWORKS:
                    if addr in network:
                        msg = f"Access to internal/private IP {ip_str} ({hostname}) is blocked"
                        raise SecurityError(msg)
            except ValueError as e_inner:
                msg = f"Invalid IP address format: {ip_str}"
                raise SecurityError(msg) from e_inner
        else:
            msg = f"Invalid IP address format: {ip_str}"
            raise SecurityError(msg) from e


async def validate_url(url: str) -> str:
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
        addr_info = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            _validate_ip(ip_str, hostname)
        if not addr_info:
            msg = f"Failed to resolve hostname {hostname}"
            raise SecurityError(msg)
        return addr_info[0][4][0]
    except OSError as e:
        # If hostname resolution fails, deny access instead of silently passing
        # to prevent bypassing SSRF checks via transient failures or DNS rebinding
        msg = f"Failed to resolve hostname {hostname}"
        raise SecurityError(msg) from e


def _normalize_for_prefix_check(path: Path) -> str:
    """Return a forward-slash path string suitable for blocked-prefix matching.

    Handles the macOS firmlink quirk where `/etc`, `/var`, `/tmp` resolve to
    `/private/etc`, `/private/var`, `/private/tmp`. We strip a leading `/private`
    so the same blocklist works identically on Linux and macOS.
    """
    path_str = str(path).replace("\\", "/")
    if path_str.startswith("/private/"):
        # /private/etc -> /etc, /private/var -> /var, /private/tmp -> /tmp
        path_str = path_str[len("/private") :]
    return path_str if path_str.endswith("/") else path_str + "/"


def _is_under_blocked_prefix(
    resolved: Path, lexical: Path, prefixes: tuple[str, ...]
) -> str | None:
    """Return the blocked prefix that ``resolved``/``lexical`` falls under, else None.

    Robust against the macOS firmlink layout (``/etc`` -> ``/private/etc``):
    each blocked prefix directory is itself canonicalized with ``realpath`` so
    the containment check compares like-for-like canonical paths rather than
    relying on a hand-rolled ``/private`` string strip. Containment uses
    ``Path.is_relative_to`` (a proper path-segment check) instead of a naive
    ``startswith``, so siblings such as ``/etc-decoy`` are not mistaken for
    ``/etc``. The pre-resolution (lexical) path is also checked so a symlink
    cannot mask an attempt that targets a blocked prefix literally.
    """
    candidates = {resolved, lexical}
    for prefix in prefixes:
        prefix_dir = Path(prefix.rstrip("/"))
        # Compare against both the literal blocked dir and its canonical form so
        # the same blocklist works on Linux and macOS firmlink layouts.
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
    # Sentinel: Expand user (`~`) before resolving to prevent TOCTOU bypasses where
    # `~` is treated as a literal local directory `~/...` during validation but expanded
    # by downstream APIs to the actual home directory `/home/user/...`.
    path = Path(file_path).expanduser().resolve()
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
    # Check BOTH the lexical (pre-resolve) and resolved paths against canonical
    # blocked dirs. On macOS `/etc` resolves to `/private/etc` via firmlinks, so
    # the helper canonicalizes each blocked prefix and uses path-segment
    # containment rather than a fragile `/private` string strip + startswith.
    lexical = Path(file_path).expanduser()
    blocked = _is_under_blocked_prefix(path, lexical, _blocked_prefixes)
    if blocked is not None:
        msg = f"Access to {blocked} is blocked for security"
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
    path = Path(output_dir).expanduser().resolve()
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
    # Check BOTH the lexical (pre-resolve) and resolved paths against canonical
    # blocked dirs (see _is_under_blocked_prefix for the macOS firmlink rationale).
    lexical = Path(output_dir).expanduser()
    blocked = _is_under_blocked_prefix(path, lexical, _blocked_prefixes)
    if blocked is not None:
        msg = f"Writing to {blocked} is blocked for security"
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


async def fetch_url_safely(
    url: str,
    timeout: float = 30.0,
    max_size: int = 50 * 1024 * 1024,  # Default 50MB
) -> bytes:
    """Fetch URL content safely by pinning the IP to prevent DNS rebinding."""
    from urllib.parse import urlunparse

    import httpx

    ip_addr = await validate_url(url)
    parsed = urlparse(url)

    # Construct a new URL using the IP address
    # We must preserve the original scheme, path, query, etc.
    # parsed.netloc might contain port, so we handle that.
    # For IPv6, we must wrap the IP in brackets.
    port_suffix = f":{parsed.port}" if parsed.port else ""
    if ":" in ip_addr:
        new_netloc = f"[{ip_addr}]{port_suffix}"
    else:
        new_netloc = f"{ip_addr}{port_suffix}"
    new_url = urlunparse(parsed._replace(netloc=new_netloc))

    headers = {"Host": parsed.hostname}
    extensions = {"sni_hostname": parsed.hostname}

    async with httpx.AsyncClient(verify=True) as client:
        # Use stream to prevent OOM / memory exhaustion DoS
        async with client.stream(
            "GET",
            new_url,
            headers=headers,
            extensions=extensions,
            timeout=timeout,
            follow_redirects=False,  # Redirects could lead to rebinding or other SSRF
        ) as resp:
            resp.raise_for_status()

            # Early check if Content-Length exceeds max_size
            content_length = resp.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > max_size:
                        msg = f"File size exceeds maximum allowed ({max_size} bytes)"
                        raise SecurityError(msg)
                except ValueError:
                    # Ignore malformed Content-Length header and rely on chunk accumulation
                    pass

            chunks = []
            accumulated_size = 0
            async for chunk in resp.aiter_bytes(chunk_size=8192):
                accumulated_size += len(chunk)
                if accumulated_size > max_size:
                    msg = f"File size exceeds maximum allowed ({max_size} bytes)"
                    raise SecurityError(msg)
                chunks.append(chunk)

            return b"".join(chunks)
