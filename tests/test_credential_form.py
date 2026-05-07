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


def test_phone_prefill_renders_value_and_activates_user_tab() -> None:
    """telegram-user E2E case: phone is in skret, bot token is not.

    Driver passes ``prefill={'TELEGRAM_PHONE': '+8412345...'}``; the form
    should render the User Mode tab as active so the user just clicks
    Connect (not retype the phone or paste a bot token instead).
    """
    html = render_telegram_credential_form(
        SCHEMA, "/auth", prefill={"TELEGRAM_PHONE": "+84123456789"}
    )
    assert 'value="+84123456789"' in html
    # User tab + panel are active; Bot tab + panel are not.
    assert 'class="tab active" data-tab="user"' in html
    assert 'class="tab" data-tab="bot"' in html
    assert 'class="tab-panel active" data-panel="user"' in html
    assert 'class="tab-panel" data-panel="bot"' in html
    # JS must initialize ``activeTab = "user"`` so subsequent click handlers
    # know which panel to read on submit.
    assert 'var activeTab = "user";' in html


def test_bot_token_prefill_keeps_bot_tab_active() -> None:
    html = render_telegram_credential_form(
        SCHEMA, "/auth", prefill={"TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"}
    )
    assert 'value="123456:ABC-DEF"' in html
    assert 'class="tab active" data-tab="bot"' in html
    assert 'class="tab" data-tab="user"' in html
    assert 'var activeTab = "bot";' in html


def test_no_prefill_defaults_to_bot_tab() -> None:
    """Without prefill, the form opens on Bot Mode (preserves prior behaviour)."""
    html = render_telegram_credential_form(SCHEMA, "/auth", prefill=None)
    assert 'class="tab active" data-tab="bot"' in html
    assert 'class="tab" data-tab="user"' in html
    # No ``value=`` attrs leaked when there's nothing to prefill.
    assert 'name="TELEGRAM_PHONE"' in html
    assert "value=" not in html.split('name="TELEGRAM_PHONE"')[1].split("/>")[0]


def test_empty_prefill_dict_is_safe() -> None:
    """Empty prefill dict treated identically to None."""
    html = render_telegram_credential_form(SCHEMA, "/auth", prefill={})
    assert 'class="tab active" data-tab="bot"' in html


def test_prefill_value_xss_escaped() -> None:
    """Prefill values must be HTML-escaped to keep value=`` attr safe."""
    html = render_telegram_credential_form(
        SCHEMA, "/auth", prefill={"TELEGRAM_PHONE": '"><script>alert(1)</script>'}
    )
    assert "<script>alert(1)</script>" not in html
    # Quotes inside the prefill must escape to ``&quot;``.
    assert "&quot;" in html


def test_dual_prefill_defaults_to_bot_mode() -> None:
    """Both bot token + phone prefilled (unusual): pick Bot Mode default.

    The current driver excludes bot+phone overlap at matrix level (each
    config picks one mode), but renderers must not crash if both arrive.
    """
    html = render_telegram_credential_form(
        SCHEMA,
        "/auth",
        prefill={"TELEGRAM_BOT_TOKEN": "abc", "TELEGRAM_PHONE": "+84"},
    )
    assert 'class="tab active" data-tab="bot"' in html


def test_phone_prefill_marks_phone_required_only() -> None:
    """User mode prefill: only phone input keeps ``required`` attr.

    Inactive Bot Mode's input must NOT have ``required`` — otherwise the
    browser blocks form submit on a hidden field with no value.
    """
    html = render_telegram_credential_form(
        SCHEMA, "/auth", prefill={"TELEGRAM_PHONE": "+84"}
    )
    phone_input = html.split('name="TELEGRAM_PHONE"')[1].split("/>")[0]
    bot_input = html.split('name="TELEGRAM_BOT_TOKEN"')[1].split("/>")[0]
    assert "required" in phone_input
    assert "required" not in bot_input


def test_bot_mode_marks_bot_token_required_only() -> None:
    """Bot mode (default): only bot token input has ``required`` attr."""
    html = render_telegram_credential_form(SCHEMA, "/auth")
    phone_input = html.split('name="TELEGRAM_PHONE"')[1].split("/>")[0]
    bot_input = html.split('name="TELEGRAM_BOT_TOKEN"')[1].split("/>")[0]
    assert "required" in bot_input
    assert "required" not in phone_input


def test_bot_token_only_prefill_marks_bot_token_required_only() -> None:
    """Bot mode with prefill: only bot token input has ``required`` attr."""
    html = render_telegram_credential_form(
        SCHEMA, "/auth", prefill={"TELEGRAM_BOT_TOKEN": "abc"}
    )
    phone_input = html.split('name="TELEGRAM_PHONE"')[1].split("/>")[0]
    bot_input = html.split('name="TELEGRAM_BOT_TOKEN"')[1].split("/>")[0]
    assert "required" in bot_input
    assert "required" not in phone_input
