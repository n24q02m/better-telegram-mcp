"""Tests for security validation module."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest

from better_telegram_mcp.backends.security import (
    SecurityError,
    validate_file_path,
    validate_output_dir,
    validate_url,
)

_IS_WINDOWS = sys.platform == "win32"


def _tilde_traversal_to(target: str) -> str:
    """Build a ``~/../..././<target>`` path that always lands on ``/<target>``.

    The number of ``..`` segments is derived from the real depth of ``~`` so
    the traversal reaches the filesystem root wherever home happens to be --
    ``/home/runner``, ``/Users/runner``, or an isolated tmp dir. Hardcoding
    two levels made these tests depend on the ambient HOME.

    Takes the deeper of the raw and resolved home (macOS resolves /var and
    /tmp through /private, so the two differ). Over-climbing is harmless:
    ``/..`` is ``/``.
    """
    home = Path.home()
    depth = max(len(home.parts), len(home.resolve().parts)) - 1
    return "/".join(["~", *([".."] * depth), target])


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

    def test_private_10_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://10.0.0.1/")

    def test_private_172_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://172.16.0.1/")

    def test_private_192_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://192.168.1.1/")

    def test_link_local_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_ipv6_loopback_blocked(self):
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://[::1]/")

    def test_ipv6_unspecified_blocked(self):
        """Ensure IPv6 unspecified address (::) is blocked directly by string check."""
        with pytest.raises(SecurityError, match="blocked"):
            validate_url("http://[::]/")

    @pytest.mark.asyncio
    async def test_fetch_url_safely_ipv6_unspecified(self):
        from better_telegram_mcp.backends.security import fetch_url_safely

        with pytest.raises(SecurityError, match="blocked"):
            await fetch_url_safely("http://[::]/")

    def test_ipv4_mapped_ipv6_loopback_blocked(self, monkeypatch):
        """IPv4-mapped IPv6 like ::ffff:127.0.0.1 must be blocked (issue #42)."""
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda host, port: [(10, 1, 6, "", ("::ffff:127.0.0.1", 80, 0, 0))],
        )
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://ipv4mapped.attacker.com/")

    def test_ipv4_mapped_ipv6_private_blocked(self, monkeypatch):
        """IPv4-mapped IPv6 like ::ffff:10.0.0.1 must be blocked (issue #42)."""
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda host, port: [(10, 1, 6, "", ("::ffff:10.0.0.1", 80, 0, 0))],
        )
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://ipv4mapped-private.attacker.com/")

    def test_zero_ip_blocked(self):
        with pytest.raises(SecurityError, match="blocked"):
            validate_url("http://0.0.0.0/")  # noqa: S104

    def test_no_hostname(self):
        with pytest.raises(SecurityError, match="no hostname"):
            validate_url("http://")

    def test_public_ip_allowed(self):
        validate_url("https://93.184.216.34/image.jpg")

    def test_dns_resolution_blocks_internal(self, monkeypatch):
        # Mock socket.getaddrinfo to simulate malicious domain resolving to 127.0.0.1
        monkeypatch.setattr(
            "socket.getaddrinfo", lambda host, port: [(2, 1, 6, "", ("127.0.0.1", 80))]
        )
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://malicious-domain-resolving-to-local.com/admin")

    def test_dns_resolution_blocks_mixed_ips(self, monkeypatch):
        """Hostnames resolving to multiple IPs (one public, one private) must be blocked."""
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda host, port: [
                (2, 1, 6, "", ("93.184.216.34", 80)),
                (2, 1, 6, "", ("10.0.0.1", 80)),
            ],
        )
        with pytest.raises(SecurityError, match="internal/private"):
            validate_url("http://mixed-ips.attacker.com/")

    def test_dns_resolution_allows_external(self, monkeypatch):
        # Mock socket.getaddrinfo to simulate benign domain resolving to public IP
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 80))],
        )
        validate_url("http://example.com/image.jpg")

    def test_dns_resolution_failure_blocked(self, monkeypatch):
        original_err = OSError("Temporary failure in name resolution")

        def mock_getaddrinfo(*args, **kwargs):
            raise original_err

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
        with pytest.raises(
            SecurityError, match="Failed to resolve hostname"
        ) as excinfo:
            validate_url("http://nonexistent.domain.internal/admin")

        # Verify exception chaining (__cause__)
        assert excinfo.value.__cause__ is original_err

    def test_dns_resolution_gaierror_blocked(self, monkeypatch):
        """socket.gaierror (subclass of OSError) is also caught and wrapped."""
        original_err = socket.gaierror(-2, "Name or service not known")

        def mock_getaddrinfo(*args, **kwargs):
            raise original_err

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
        with pytest.raises(
            SecurityError, match="Failed to resolve hostname"
        ) as excinfo:
            validate_url("http://gaierror.attacker.com/")

        assert excinfo.value.__cause__ is original_err

    def test_dns_resolution_empty_result_allowed(self, monkeypatch):
        """If hostname resolves to empty result list, it is blocked (resolution failure)."""
        monkeypatch.setattr("socket.getaddrinfo", lambda host, port: [])
        with pytest.raises(SecurityError, match="Failed to resolve hostname"):
            validate_url("http://resolves-to-nothing.com/")

    @pytest.mark.asyncio
    async def test_fetch_url_safely_prevents_rebinding(self, monkeypatch):
        """Test that fetch_url_safely uses the validated IP and ignores subsequent DNS changes."""
        from unittest.mock import MagicMock, patch

        import httpx

        from better_telegram_mcp.backends.security import fetch_url_safely

        target_hostname = "rebinding.attacker.com"
        safe_ip = "93.184.216.34"
        malicious_ip = "127.0.0.1"

        # State to simulate rebinding: first call returns safe IP, subsequent returns malicious IP
        resolution_count = 0

        def mock_getaddrinfo(host, port, *args, **kwargs):
            nonlocal resolution_count
            resolution_count += 1
            if resolution_count == 1:
                return [(2, 1, 6, "", (safe_ip, 80))]
            return [(2, 1, 6, "", (malicious_ip, 80))]

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        # Mock httpx.AsyncClient.stream to verify the URL used
        with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
            resp = httpx.Response(200)
            resp._request = httpx.Request("GET", f"http://{safe_ip}/data")

            async def mock_aiter_bytes(chunk_size=None):
                yield b"content"

            resp.aiter_bytes = mock_aiter_bytes

            mock_stream.return_value.__aenter__.return_value = resp

            await fetch_url_safely(f"http://{target_hostname}/data")

            # Verify httpx.stream was called with the SAFE IP in the URL, not the hostname
            args, _ = mock_stream.call_args
            requested_url = str(args[1])
            assert safe_ip in requested_url
            assert malicious_ip not in requested_url
            assert target_hostname not in requested_url

    async def test_fetch_url_safely_ipv6(self, monkeypatch):
        """Verify fetch_url_safely correctly constructs URL with IPv6 address."""
        from unittest.mock import MagicMock, patch

        import httpx

        from better_telegram_mcp.backends.security import fetch_url_safely

        target_hostname = "ipv6.example.com"
        safe_ip = "2606:4700:4700::1111"

        def mock_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET6, 1, 6, "", (safe_ip, 8080, 0, 0))]

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
            resp = httpx.Response(200)
            resp._request = httpx.Request("GET", f"http://[{safe_ip}]:8080/data")

            async def mock_aiter_bytes(chunk_size=None):
                yield b"content"

            resp.aiter_bytes = mock_aiter_bytes

            mock_stream.return_value.__aenter__.return_value = resp

            await fetch_url_safely(f"http://{target_hostname}:8080/data")

            args, kwargs = mock_stream.call_args
            requested_url = str(args[1])
            assert requested_url == f"http://[{safe_ip}]:8080/data"
            assert kwargs["headers"]["Host"] == target_hostname
            assert kwargs["extensions"]["sni_hostname"] == target_hostname

    async def test_fetch_url_safely_max_size_content_length(self, monkeypatch):
        """Verify fetch_url_safely rejects files larger than max_size based on Content-Length."""
        from unittest.mock import MagicMock, patch

        import httpx

        from better_telegram_mcp.backends.security import (
            SecurityError,
            fetch_url_safely,
        )

        target_hostname = "example.com"
        safe_ip = "93.184.216.34"

        def mock_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET, 1, 6, "", (safe_ip, 80, 0, 0))]

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
            resp = httpx.Response(200, headers={"Content-Length": "101"})
            resp._request = httpx.Request("GET", f"http://{safe_ip}/data")

            mock_stream.return_value.__aenter__.return_value = resp

            import pytest

            with pytest.raises(
                SecurityError, match="File size exceeds maximum allowed"
            ):
                await fetch_url_safely(f"http://{target_hostname}/data", max_size=100)

    async def test_fetch_url_safely_max_size_accumulated(self, monkeypatch):
        """Verify fetch_url_safely rejects files larger than max_size based on accumulated chunks."""
        from unittest.mock import MagicMock, patch

        import httpx

        from better_telegram_mcp.backends.security import (
            SecurityError,
            fetch_url_safely,
        )

        target_hostname = "example.com"
        safe_ip = "93.184.216.34"

        def mock_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET, 1, 6, "", (safe_ip, 80, 0, 0))]

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)

        with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:
            resp = httpx.Response(200)
            resp._request = httpx.Request("GET", f"http://{safe_ip}/data")

            async def mock_aiter_bytes(chunk_size=None):
                yield b"chunk1 "
                yield b"chunk2 "
                yield b"chunk3"

            resp.aiter_bytes = mock_aiter_bytes

            mock_stream.return_value.__aenter__.return_value = resp

            import pytest

            # Total size is 21 bytes. Let's limit it to 10
            with pytest.raises(
                SecurityError, match="File size exceeds maximum allowed"
            ):
                await fetch_url_safely(f"http://{target_hostname}/data", max_size=10)


class TestValidateFilePath:
    def test_normal_path_allowed(self, tmp_path):
        photo = tmp_path / "photo.jpg"
        result = validate_file_path(str(photo))
        assert result == photo.resolve()

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
        # We can't easily create a link to /etc/passwd in some restricted environments,
        # but we can try to link to any path that starts with a blocked prefix.
        try:
            os.symlink("/etc/passwd", link)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path(str(link))

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only symlinks/firmlinks")
    def test_symlink_to_blocked_dir_canonicalized(self, tmp_path):
        """A symlinked directory pointing at /etc must be blocked after realpath.

        This is the macOS-firmlink / symlink bypass: the symlink itself lives in
        an allowed location, so a lexical check passes, but canonicalizing the
        target reveals it lands under a blocked prefix (/etc, which on macOS is
        the firmlink /private/etc).
        """
        link = tmp_path / "etc_link"
        try:
            os.symlink("/etc", link)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path(str(link / "passwd"))

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_sibling_prefix_not_blocked(self):
        """A path that merely shares a name prefix with a blocked dir is allowed.

        The containment check is per path-segment (is_relative_to), so
        ``/etc-decoy`` is NOT treated as being under ``/etc``.
        """
        # Non-existent sibling-prefix path resolves lexically and must pass the
        # blocked-prefix gate (it is rejected later only if it hits another rule).
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
        # This resolves to /home/<user>/.ssh/id_rsa, which contains a hidden directory
        with pytest.raises(SecurityError, match="hidden"):
            validate_file_path("~/.ssh/id_rsa")

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_tilde_expansion_traversal_blocked(self):
        """Test that paths like ~/../../etc/passwd are expanded and blocked."""
        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path(_tilde_traversal_to("etc/passwd"))


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
            validate_output_dir(_tilde_traversal_to("etc/cron.d"))
