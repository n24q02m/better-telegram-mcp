"""Tests for security validation module."""

from __future__ import annotations

import sys

import pytest

from better_telegram_mcp.backends.security import (
    SecurityError,
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

    def test_dns_resolution_allows_external(self, monkeypatch):
        # Mock socket.getaddrinfo to simulate benign domain resolving to public IP
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 80))],
        )
        validate_url("http://example.com/image.jpg")

    def test_dns_resolution_failure_blocked(self, monkeypatch):
        def mock_getaddrinfo(*args, **kwargs):
            raise OSError("Temporary failure in name resolution")

        monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
        with pytest.raises(SecurityError, match="Failed to resolve hostname"):
            validate_url("http://nonexistent.domain.internal/admin")


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

    def test_allowed_dir_enforcement(self, tmp_path):
        photo = tmp_path / "photo.jpg"
        allowed = tmp_path / "uploads"
        with pytest.raises(SecurityError, match="must be within"):
            validate_file_path(str(photo), allowed_dir=allowed)

    def test_allowed_dir_ok(self, tmp_path):
        photo = tmp_path / "photo.jpg"
        result = validate_file_path(str(photo), allowed_dir=tmp_path)
        assert result == photo.resolve()


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

    @pytest.mark.skipif(_IS_WINDOWS, reason="Unix-only blocked paths")
    def test_var_spool_blocked(self):
        with pytest.raises(SecurityError, match="/var/spool/"):
            validate_output_dir("/var/spool/cron")
