"""Tests for security validation module."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from better_telegram_mcp.backends.security import (
    SecurityError,
    SSRFProtectedNetworkBackend,
    _normalize_for_prefix_check,
    fetch_url_safely,
    validate_file_path,
    validate_output_dir,
    validate_url,
)

_IS_WINDOWS = sys.platform == "win32"


class TestValidateUrl:
    def test_https_allowed(self):
        validate_url("https://example.com/photo.jpg")

    def test_http_allowed(self):
        validate_url("http://example.com/photo.jpg")

    def test_ftp_blocked(self):
        with pytest.raises(SecurityError, match="Only http/https"):
            validate_url("ftp://example.com/file")

    def test_file_blocked(self):
        with pytest.raises(SecurityError, match="Only http/https"):
            validate_url("file:///etc/passwd")

    def test_localhost_blocked(self):
        with pytest.raises(SecurityError, match="blocked"):
            validate_url("http://localhost/admin")

    def test_127_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://127.0.0.1/admin")

    def test_metadata_endpoint_blocked(self):
        with pytest.raises(SecurityError, match="metadata"):
            validate_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_metadata_ip_blocked(self):
        with pytest.raises(SecurityError, match="metadata"):
            validate_url("http://169.254.169.254/")

    def test_private_10_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://10.0.0.1/")

    def test_private_172_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://172.16.0.1/")

    def test_private_192_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://192.168.1.1/")

    def test_zero_ip_blocked(self):
        with pytest.raises(SecurityError, match="blocked"):
            validate_url("http://0.0.0.0/")  # noqa: S104

    def test_no_hostname(self):
        with pytest.raises(SecurityError, match="no hostname"):
            validate_url("http://")

    def test_public_ip_allowed(self):
        validate_url("https://93.184.216.34/image.jpg")


class TestSSRFProtectedBackend:
    @pytest.mark.asyncio
    async def test_connect_tcp_pins_ip(self, monkeypatch):
        """Verify that connect_tcp resolves and pins the safe IP."""
        safe_ip = "93.184.216.34"
        backend = SSRFProtectedNetworkBackend()

        # Mock socket.getaddrinfo to return a safe IP
        mock_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (safe_ip, 80))]

        def mock_getaddrinfo(*args, **kwargs):
            return mock_addrinfo

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        # Mock the parent's connect_tcp to verify the pinned IP is passed
        with patch(
            "httpcore.AnyIOBackend.connect_tcp", new_callable=AsyncMock
        ) as mock_super:
            await backend.connect_tcp("example.com", 80)
            args, kwargs = mock_super.call_args
            assert args[0] == safe_ip

    @pytest.mark.asyncio
    async def test_connect_tcp_blocks_private_ip(self, monkeypatch):
        """Verify that connect_tcp blocks private IPs after resolution."""
        malicious_ip = "127.0.0.1"
        backend = SSRFProtectedNetworkBackend()

        def mock_getaddrinfo(*args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (malicious_ip, 80))]

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        with pytest.raises(SecurityError, match="internal/private"):
            await backend.connect_tcp("attacker.com", 80)

    @pytest.mark.asyncio
    async def test_connect_unix_socket_blocked(self):
        """Verify that unix socket connections are explicitly blocked."""
        backend = SSRFProtectedNetworkBackend()
        with pytest.raises(SecurityError, match="Unix socket"):
            await backend.connect_unix_socket("/var/run/docker.sock")


class TestFetchUrlSafely:
    @pytest.mark.asyncio
    async def test_fetch_url_safely_ipv6_header(self, monkeypatch):
        """Verify fetch_url_safely handles IPv6 correctly in the Host header."""

        safe_ipv6 = "2606:4700:4700::1111"

        # Mock the backend to return success
        class MockStream(AsyncMock):
            async def aclose(self):
                pass

        async def mock_connect_tcp(host, port, **kwargs):
            return MockStream()

        with patch(
            "better_telegram_mcp.backends.security.SSRFProtectedNetworkBackend.connect_tcp",
            side_effect=mock_connect_tcp,
        ):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                resp = httpx.Response(200, content=b"content")
                resp._request = httpx.Request("GET", f"http://[{safe_ipv6}]/")
                mock_get.return_value = resp

                await fetch_url_safely(f"http://[{safe_ipv6}]/")

                # Verify original URL with brackets was passed to client
                args, _ = mock_get.call_args
                assert str(args[0]) == f"http://[{safe_ipv6}]/"

    @pytest.mark.asyncio
    async def test_ipv4_mapped_ipv6_loopback_blocked(self, monkeypatch):
        """IPv4-mapped IPv6 like ::ffff:127.0.0.1 must be blocked via the backend."""
        backend = SSRFProtectedNetworkBackend()

        def mock_getaddrinfo(*args, **kwargs):
            return [
                (
                    socket.AF_INET6,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("::ffff:127.0.0.1", 80, 0, 0),
                )
            ]

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        with pytest.raises(SecurityError, match="internal/private"):
            await backend.connect_tcp("ipv4mapped.attacker.com", 80)


class TestValidateFilePath:
    def test_normal_path_allowed(self, tmp_path):
        photo = tmp_path / "photo.jpg"
        result = validate_file_path(str(photo))
        assert result == photo.resolve()

    def test_macos_firmlink_normalization(self):
        """Verify _normalize_for_prefix_check handles /private prefix."""
        assert (
            _normalize_for_prefix_check(Path("/private/etc/passwd")) == "/etc/passwd/"
        )
        assert _normalize_for_prefix_check(Path("/etc/passwd")) == "/etc/passwd/"

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_etc_passwd_blocked(self):
        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path("/etc/passwd")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_proc_blocked(self):
        with pytest.raises(SecurityError, match="/proc/"):
            validate_file_path("/proc/self/environ")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_root_blocked(self):
        with pytest.raises(SecurityError, match="/root/"):
            validate_file_path("/root/.bashrc")

    def test_dotfiles_blocked(self):
        with pytest.raises(SecurityError, match="hidden"):
            validate_file_path("/home/user/.ssh/id_rsa")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only path traversal")
    def test_traversal_resolved(self):
        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path("/tmp/../etc/passwd")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only symlinks")
    def test_symlink_traversal_blocked(self, tmp_path):
        """Test that a symlink pointing to a blocked path is correctly rejected."""
        link = tmp_path / "malicious_link"
        try:
            os.symlink("/etc/passwd", link)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path(str(link))

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only symlinks/firmlinks")
    def test_symlink_to_blocked_dir_canonicalized(self, tmp_path):
        """A symlinked directory pointing at /etc must be blocked after realpath."""
        link = tmp_path / "etc_link"
        try:
            os.symlink("/etc", link)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path(str(link / "passwd"))

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_sibling_prefix_not_blocked(self):
        """A path that merely shares a name prefix with a blocked dir is allowed."""
        result = validate_file_path("/etcdecoy/file.txt")
        assert str(result).endswith("file.txt")

    def test_allowed_dir_enforcement(self, tmp_path):
        photo = tmp_path / "photo.jpg"
        allowed = tmp_path / "uploads"
        with pytest.raises(SecurityError, match="must be within"):
            validate_file_path(str(photo), allowed_dir=allowed)

    def test_allowed_dir_ok(self, tmp_path):
        photo = tmp_path / "photo.jpg"
        result = validate_file_path(str(photo), allowed_dir=tmp_path)
        assert result == photo.resolve()

    def test_complex_allowed_dir_containment(self, tmp_path):
        """Test containment check with complex paths."""
        allowed = tmp_path / "data"
        allowed.mkdir()
        sub_dir = allowed / "nested/folder"
        sub_dir.mkdir(parents=True)
        target = sub_dir / "file.txt"

        # Valid nested path
        result = validate_file_path(str(target), allowed_dir=allowed)
        assert result == target.resolve()

        # Path with .. that stays inside
        result = validate_file_path(
            str(sub_dir / "../folder/file.txt"), allowed_dir=allowed
        )
        assert result == target.resolve()

        # Path with .. that escapes
        with pytest.raises(SecurityError, match="must be within"):
            validate_file_path(str(allowed / "../other.txt"), allowed_dir=allowed)

    def test_tilde_expansion_blocked(self):
        """Test that paths starting with ~ are expanded and properly blocked."""
        with pytest.raises(SecurityError, match="hidden"):
            validate_file_path("~/.ssh/id_rsa")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_tilde_expansion_traversal_blocked(self):
        """Test that paths like ~/../../etc/passwd are expanded and blocked."""
        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path("~/../../etc/passwd")


class TestValidateOutputDir:
    def test_normal_dir_allowed(self, tmp_path):
        downloads = tmp_path / "downloads"
        result = validate_output_dir(str(downloads))
        assert result == downloads.resolve()

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_etc_blocked(self):
        with pytest.raises(SecurityError, match="/etc/"):
            validate_output_dir("/etc/cron.d")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_usr_blocked(self):
        with pytest.raises(SecurityError, match="/usr/"):
            validate_output_dir("/usr/bin")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_sbin_blocked(self):
        with pytest.raises(SecurityError):
            validate_output_dir("/sbin/")

    def test_hidden_dir_blocked(self):
        with pytest.raises(SecurityError, match="hidden"):
            validate_output_dir("/home/user/.ssh")

    def test_base_dir_enforcement(self, tmp_path):
        data = tmp_path / "data"
        base = tmp_path / "downloads"
        with pytest.raises(SecurityError, match="must be within"):
            validate_output_dir(str(data), base_dir=base)

    def test_complex_base_dir_containment(self, tmp_path):
        """Test containment check for output directory."""
        base = tmp_path / "app"
        base.mkdir()
        target = base / "logs/daily"

        # Valid nested path
        result = validate_output_dir(str(target), base_dir=base)
        assert result == target.resolve()

        # Escape via ..
        with pytest.raises(SecurityError, match="must be within"):
            validate_output_dir(str(base / "../../etc"), base_dir=base)

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_var_spool_blocked(self):
        with pytest.raises(SecurityError, match="/var/spool/"):
            validate_output_dir("/var/spool/cron")

    def test_tilde_expansion_blocked(self):
        """Test that paths starting with ~ are expanded and properly blocked."""
        with pytest.raises(SecurityError, match="hidden"):
            validate_output_dir("~/.ssh")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_tilde_expansion_traversal_blocked(self):
        """Test that paths like ~/../../etc/cron.d are expanded and blocked."""
        with pytest.raises(SecurityError, match="/etc/"):
            validate_output_dir("~/../../etc/cron.d")


class TestSSRFRedirects:
    @pytest.mark.asyncio
    async def test_backend_blocks_redirect_target(self, monkeypatch):
        """Verify that the backend catches internal IPs during redirects."""
        backend = SSRFProtectedNetworkBackend()

        def mock_getaddrinfo(host, port, **kwargs):
            if host == "127.0.0.1":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
            return []

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        with pytest.raises(SecurityError, match="internal/private"):
            await backend.connect_tcp("127.0.0.1", 80)
