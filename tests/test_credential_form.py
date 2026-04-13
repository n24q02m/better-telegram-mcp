"""Tests for the telegram custom credential form renderer."""

from __future__ import annotations

from better_telegram_mcp.credential_form import render_telegram_credential_form

SCHEMA: dict = {
    "server": "better-telegram-mcp",
    "displayName": "Telegram MCP",
    "description": "Bot or User mode",
}


def test_renders_complete_html() -> None:
    html = render_telegram_credential_form(SCHEMA, "/authorize?nonce=abc")
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html
    assert "Telegram MCP" in html


def test_contains_two_tabs() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    assert "Bot Mode" in html
    assert "User Mode" in html
    assert 'data-tab="bot"' in html
    assert 'data-tab="user"' in html


def test_contains_bot_token_field() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    assert "TELEGRAM_BOT_TOKEN" in html
    assert "BotFather" in html


def test_contains_phone_field() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    assert "TELEGRAM_PHONE" in html
    assert "MTProto" in html


def test_posts_to_submit_url() -> None:
    html = render_telegram_credential_form(SCHEMA, "/authorize?nonce=xyz")
    assert "/authorize?nonce=xyz" in html


def test_supports_otp_multi_step() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    assert "otp_required" in html
    assert "password_required" in html
    assert "/otp" in html


def test_uses_safe_dom_methods() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    assert "createElement" in html
    assert "textContent" in html


def test_collects_only_active_tab_fields() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    assert ".tab-panel.active" in html


def test_escapes_display_name_xss() -> None:
    malicious = {
        "server": "x",
        "displayName": '<script>alert("xss")</script>',
        "description": "",
    }
    html = render_telegram_credential_form(malicious, "/auth")
    assert '<script>alert("xss")</script>' not in html
    assert "&lt;script&gt;" in html


def test_escapes_submit_url() -> None:
    html = render_telegram_credential_form(SCHEMA, '/auth"><script>alert(1)</script>')
    assert '"><script>' not in html
    assert "&lt;script&gt;" in html or "&quot;&gt;&lt;script&gt;" in html


def test_renders_with_minimal_schema() -> None:
    html = render_telegram_credential_form({}, "/auth")
    # Falls back to generic defaults without raising.
    assert "<!DOCTYPE html>" in html
    assert "Telegram MCP" in html or "better-telegram-mcp" in html


def test_description_omitted_when_empty() -> None:
    html = render_telegram_credential_form(
        {"server": "s", "displayName": "d", "description": ""}, "/auth"
    )
    assert 'class="server-description"' not in html


def test_tabs_default_active_is_bot() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    # The Bot tab button must be initially active.
    assert 'class="tab active" data-tab="bot"' in html
    assert 'class="tab" data-tab="user"' in html


def test_has_submit_button_and_status_box() -> None:
    html = render_telegram_credential_form(SCHEMA, "/auth")
    assert 'id="submit-btn"' in html
    assert 'id="status-box"' in html
