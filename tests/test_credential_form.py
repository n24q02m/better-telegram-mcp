"""Tests for the telegram credential form.

The renderer was de-forked onto mcp-core's shared ``render_credential_form``
(schema-level ``tabs`` capability, mcp-core >=1.20.0b1); the shared renderer
owns the form and multi-step flow, while ``relay_schema.render_telegram_form``
adds the ``initial_tab`` hint and the attach-once password-toggle enhancement.
contract that survives the de-fork: the Bot/User field set, the two tabs, the
default-active tab + prefill-driven initial tab, active-panel-only submit, the
OTP/2FA step chain, ``redirect_url`` follow, and XSS-safety.

De-fork behaviour changes vs the old forked template (each covered below):
  * ``required`` is now static per field (both tabs' inputs carry it) rather
    than toggled to the active tab. Safe: the form is ``novalidate`` and submit
    validates only ``.tab-panel.active`` fields, so the inactive input is never
    read (see ``test_both_tab_fields_are_required``).
  * The server injects the password show/hide toggle after the shared
    renderer returns HTML; the shared renderer still does not emit this
    decoration or the per-field ``autocomplete`` / ``inputmode`` hints (bot
    ``current-password``, phone ``tel``, OTP ``one-time-code``).
"""

from __future__ import annotations

from better_telegram_mcp.relay_schema import render_telegram_form

SCHEMA: dict = {
    "server": "better-telegram-mcp",
    "displayName": "Telegram MCP",
    "description": "Bot or User mode",
}


def test_renders_complete_html() -> None:
    html = render_telegram_form(SCHEMA, "/authorize?nonce=abc")
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html
    assert "Telegram MCP" in html


def test_renders_via_core_tabbed_renderer() -> None:
    """The form is drawn by mcp-core's shared tabbed renderer (schema-level
    ``tabs``), not a forked template: ARIA tablist markup is present.
    """
    html = render_telegram_form(SCHEMA, "/auth")
    assert 'role="tablist"' in html
    assert 'role="tab"' in html
    assert 'role="tabpanel"' in html
    assert 'aria-controls="panel-bot"' in html


def test_contains_two_tabs() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    assert "Bot Mode" in html
    assert "User Mode" in html
    assert 'data-tab="bot"' in html
    assert 'data-tab="user"' in html


def test_contains_bot_token_field() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    assert "TELEGRAM_BOT_TOKEN" in html
    assert "BotFather" in html


def test_contains_phone_field() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    assert "TELEGRAM_PHONE" in html
    assert "MTProto" in html


def test_posts_to_submit_url() -> None:
    html = render_telegram_form(SCHEMA, "/authorize?nonce=xyz")
    assert "/authorize?nonce=xyz" in html


def test_supports_otp_multi_step() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    assert "otp_required" in html
    assert "password_required" in html
    assert "/otp" in html


def test_uses_safe_dom_methods() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    assert "createElement" in html
    assert "textContent" in html


def test_collects_only_active_tab_fields() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    assert ".tab-panel.active" in html


def test_both_tab_fields_are_required() -> None:
    """De-fork change: ``required`` is set statically per field (both bot token
    and phone declare ``required: True``), replacing the fork's dynamic
    per-active-tab toggling. This is safe because the form is ``novalidate`` and
    the submit handler validates ONLY the active panel's fields
    (``.tab-panel.active``), so the inactive tab's ``required`` input is never
    read — the effective contract (fill the one field of your chosen mode) is
    unchanged.
    """
    html = render_telegram_form(SCHEMA, "/auth")
    bot_input = html.split('name="TELEGRAM_BOT_TOKEN"')[1].split("/>")[0]
    phone_input = html.split('name="TELEGRAM_PHONE"')[1].split("/>")[0]
    assert "required" in bot_input
    assert "required" in phone_input
    assert ".tab-panel.active" in html


def test_form_follows_redirect_url_on_success() -> None:
    """OAuth relay invariant (relay-flow.md 6.5): on success the form must
    follow ``redirect_url`` so an external OAuth client callback receives the
    code. mcp-core's tabbed renderer stashes ``pendingRedirectUrl`` and calls
    ``window.location.replace`` in the direct-submit and async completion
    branches.
    """
    html = render_telegram_form(SCHEMA, "/auth")
    assert "pendingRedirectUrl" in html
    assert "window.location.replace" in html


def test_escapes_display_name_xss() -> None:
    malicious = {
        "server": "x",
        "displayName": '<script>alert("xss")</script>',
        "description": "",
    }
    html = render_telegram_form(malicious, "/auth")
    assert '<script>alert("xss")</script>' not in html
    assert "&lt;script&gt;" in html


def test_escapes_submit_url() -> None:
    html = render_telegram_form(SCHEMA, '/auth"><script>alert(1)</script>')
    assert '"><script>' not in html
    assert "&lt;script&gt;" in html or "&quot;&gt;&lt;script&gt;" in html


def test_renders_with_minimal_schema() -> None:
    html = render_telegram_form({}, "/auth")
    # Falls back to generic defaults without raising.
    assert "<!DOCTYPE html>" in html
    assert "Telegram MCP" in html or "better-telegram-mcp" in html


def test_description_omitted_when_empty() -> None:
    html = render_telegram_form(
        {"server": "s", "displayName": "d", "description": ""}, "/auth"
    )
    assert 'class="server-description"' not in html


def test_tabs_default_active_is_bot() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    # The Bot tab button must be initially active.
    assert 'class="tab active" data-tab="bot"' in html
    assert 'class="tab" data-tab="user"' in html


def test_has_submit_button_and_status_box() -> None:
    html = render_telegram_form(SCHEMA, "/auth")
    assert 'id="submit-btn"' in html
    assert 'id="status-box"' in html


def test_phone_prefill_renders_value_and_activates_user_tab() -> None:
    """telegram-user E2E case: phone is in skret, bot token is not.

    Driver passes ``prefill={'TELEGRAM_PHONE': '+8412345...'}``; the form
    should render the User Mode tab as active so the user just clicks
    Connect (not retype the phone or paste a bot token instead).
    """
    html = render_telegram_form(
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
    html = render_telegram_form(
        SCHEMA, "/auth", prefill={"TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"}
    )
    assert 'value="123456:ABC-DEF"' in html
    assert 'class="tab active" data-tab="bot"' in html
    assert 'class="tab" data-tab="user"' in html
    assert 'var activeTab = "bot";' in html


def test_no_prefill_defaults_to_bot_tab() -> None:
    """Without prefill, the form opens on Bot Mode (preserves prior behaviour)."""
    html = render_telegram_form(SCHEMA, "/auth", prefill=None)
    assert 'class="tab active" data-tab="bot"' in html
    assert 'class="tab" data-tab="user"' in html
    # No ``value=`` attrs leaked when there's nothing to prefill.
    assert 'name="TELEGRAM_PHONE"' in html
    assert "value=" not in html.split('name="TELEGRAM_PHONE"')[1].split("/>")[0]


def test_empty_prefill_dict_is_safe() -> None:
    """Empty prefill dict treated identically to None."""
    html = render_telegram_form(SCHEMA, "/auth", prefill={})
    assert 'class="tab active" data-tab="bot"' in html


def test_prefill_value_xss_escaped() -> None:
    """Prefill values must be HTML-escaped to keep value=`` attr safe."""
    html = render_telegram_form(
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
    html = render_telegram_form(
        SCHEMA,
        "/auth",
        prefill={"TELEGRAM_BOT_TOKEN": "abc", "TELEGRAM_PHONE": "+84"},
    )
    assert 'class="tab active" data-tab="bot"' in html


def test_form_has_xss_safe_submit_url_handling() -> None:
    """Submit URL is HTML-escaped on insertion (defense in depth).

    A malicious nonce containing ``"`` must not break out of the JS string
    literal. The renderer uses ``html.escape(..., quote=True)`` which converts
    ``"`` to ``&quot;`` before insertion.
    """
    evil_url = '/authorize?nonce="><script>alert(1)</script>'
    html = render_telegram_form(SCHEMA, evil_url)
    # Must NOT contain the raw evil URL anywhere
    assert '"><script>' not in html
    # Should contain the escaped form
    assert "&quot;&gt;&lt;script&gt;" in html


def test_password_toggle_tracks_recycled_field_identity() -> None:
    """Data-field changes reset the visible and ARIA SHOW/HIDE state."""
    html = render_telegram_form(SCHEMA, "/auth")
    assert 'var lf = i.dataset.field || "";' in html
    assert 'if((i.dataset.field || "") !== lf)' in html
    assert (
        'b.textContent = "SHOW"; b.setAttribute("aria-label", "Show password"); b.setAttribute("aria-pressed", "false");'
        in html
    )


def test_password_toggle_attaches_static_and_dynamic_inputs_once() -> None:
    """Static and recycled step inputs share one guarded attachment path."""
    html = render_telegram_form(SCHEMA, "/auth")
    assert "if(i.dataset.hasToggle) return;" in html
    assert 'i.dataset.hasToggle = "true";' in html
    assert "if(botToken) attach(botToken);" in html
    assert "if(stepInp) attach(stepInp);" in html
    assert 'attributeFilter: ["disabled", "type", "data-field"]' in html
