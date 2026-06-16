"""Tests for Settings.cf_mode property."""

from better_telegram_mcp.config import Settings


def test_cf_mode_true_when_cf_kv(monkeypatch):
    monkeypatch.setenv("MCP_STORAGE_BACKEND", "cf-kv")
    s = Settings()
    assert s.cf_mode is True


def test_cf_mode_false_by_default(monkeypatch):
    monkeypatch.delenv("MCP_STORAGE_BACKEND", raising=False)
    s = Settings()
    assert s.cf_mode is False
