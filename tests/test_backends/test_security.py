"""Tests for security validation module."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest

from better_telegram_mcp.backends.security import (
    SecurityError,
    _normalize_for_prefix_check,
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
        """If hostname resolves to empty result list, it passes validation."""
        monkeypatch.setattr("socket.getaddrinfo", lambda host, port: [])
        validate_url("http://resolves-to-nothing.com/")


class TestValidateFilePath:
    def test_normal_path_allowed(self, tmp_path):
        photo = tmp_path / "photo.jpg"
        result = validate_file_path(str(photo))
        assert result == photo.resolve()

    def test_macos_firmlink_normalization(self):
        """Verify _normalize_for_prefix_check handles /private prefix."""
        # This covers the line 77 coverage gap
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
        # We can't easily create a link to /etc/passwd in some restricted environments,
        # but we can try to link to any path that starts with a blocked prefix.
        try:
            os.symlink("/etc/passwd", link)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        with pytest.raises(SecurityError, match="/etc/"):
            validate_file_path(str(link))

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
