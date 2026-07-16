"""Config schema for relay page setup.

Local OAuth form uses flat fields (bot token + phone).
User fills ONE of the two: bot token for bot mode, phone for user mode.
Relay page uses modes for tabbed UI — kept as RELAY_SCHEMA_MODES for backward compat.

The credential form is rendered by mcp-core's shared ``render_credential_form``
(schema-level ``tabs`` capability, mcp-core >=1.20.0b1) via
:func:`render_telegram_form` — no forked renderer. ``RELAY_SCHEMA`` stays the
flat server-side contract passed to ``run_http_server`` (drives
``is_schema_complete`` + form metadata); ``TELEGRAM_TABS`` is the Bot/User tab
layout the core renderer draws.
"""

from typing import Any

from mcp_core.auth import render_credential_form

RELAY_SCHEMA: dict[str, Any] = {
    "server": "better-telegram-mcp",
    "displayName": "Telegram MCP",
    "description": "Enter Bot Token for bot mode, OR Phone Number for user mode (MTProto).",
    "fields": [
        {
            "key": "TELEGRAM_BOT_TOKEN",
            "label": "Bot Token",
            "type": "password",
            "placeholder": "123456:ABC-DEF...",
            "helpUrl": "https://core.telegram.org/bots#botfather",
            "helpText": "Get from @BotFather on Telegram. Leave empty for user mode.",
            "required": False,
        },
        {
            "key": "TELEGRAM_PHONE",
            "label": "Phone Number (User Mode)",
            "type": "tel",
            "placeholder": "+84...",
            "helpText": "Full account access via MTProto. Leave empty for bot mode.",
            "required": False,
        },
    ],
    "capabilityInfo": [
        {
            "label": "Bot Mode",
            "priority": "Bot Token",
            "description": "Send/receive messages via Bot API. Limited to bot permissions.",
        },
        {
            "label": "User Mode",
            "priority": "Phone + OTP",
            "description": "Full account access via MTProto (Telethon). Requires phone verification.",
        },
    ],
}

RELAY_SCHEMA_MODES: dict[str, Any] = {
    "server": "better-telegram-mcp",
    "displayName": "Telegram MCP",
    "modes": [
        {
            "id": "bot",
            "label": "Bot Mode",
            "description": "Use a Telegram Bot token",
            "fields": [
                {
                    "key": "TELEGRAM_BOT_TOKEN",
                    "label": "Bot Token",
                    "type": "password",
                    "placeholder": "123456:ABC-DEF...",
                    "helpUrl": "https://core.telegram.org/bots#botfather",
                    "helpText": "Get from @BotFather on Telegram",
                }
            ],
        },
        {
            "id": "user",
            "label": "User Mode (MTProto)",
            "description": "Full account access",
            "fields": [
                {
                    "key": "TELEGRAM_PHONE",
                    "label": "Phone Number",
                    "type": "tel",
                    "placeholder": "+84...",
                },
            ],
        },
    ],
}

# Tab layout for the credential form. Two mutually-exclusive credential modes;
# only the active tab's field is collected on submit (mcp-core's ``tabs``
# renderer scopes the POST to ``.tab-panel.active``), so bot mode sends only
# ``TELEGRAM_BOT_TOKEN`` and user mode sends only ``TELEGRAM_PHONE`` — exactly
# what ``credential_state.save_credentials`` keys its mode detection on. Both
# fields are ``required`` so the active tab enforces a non-empty value client
# side; the inactive tab's field is never read (form is ``novalidate``).
TELEGRAM_TABS: list[dict[str, Any]] = [
    {
        "id": "bot",
        "label": "Bot Mode",
        "fields": [
            {
                "key": "TELEGRAM_BOT_TOKEN",
                "label": "Bot Token",
                "type": "password",
                "required": True,
                "placeholder": "123456:ABC-DEF...",
                "helpText": "Get from @BotFather on Telegram",
                "helpUrl": "https://core.telegram.org/bots#botfather",
            }
        ],
    },
    {
        "id": "user",
        "label": "User Mode",
        "fields": [
            {
                "key": "TELEGRAM_PHONE",
                "label": "Phone Number",
                "type": "tel",
                "required": True,
                "placeholder": "+84...",
                "helpText": (
                    "Full account access via MTProto. "
                    "OTP verification required after submit."
                ),
            }
        ],
    },
]


def render_telegram_form(
    schema: dict[str, Any],
    submit_url: str,
    prefill: dict[str, str] | None = None,
) -> str:
    """Render the Telegram credential form via mcp-core's tabbed renderer.

    Matches the ``custom_credential_form_html`` callback contract
    (``(schema, submit_url, *, prefill) -> html``) that ``run_http_server``
    invokes. The only server-side rendering logic left after the de-fork is the
    ``initial_tab`` hint: when the driver prefills a phone but no bot token
    (the ``telegram-user`` E2E case), open on the User tab so the user just
    clicks Connect instead of retyping the phone or pasting a bot token. Bot-only
    and dual prefill default to Bot. Field layout, tab switching, active-panel
    submit, OTP/2FA step chaining, and ``redirect_url`` follow all live in
    mcp-core's ``render_credential_form``.

    ``schema`` supplies the page metadata (server / displayName / description);
    ``TELEGRAM_TABS`` supplies the Bot/User field layout.
    """
    prefill = prefill or {}
    initial_tab = (
        "user"
        if prefill.get("TELEGRAM_PHONE") and not prefill.get("TELEGRAM_BOT_TOKEN")
        else "bot"
    )
    render_schema: dict[str, Any] = {
        "server": schema.get("server", "better-telegram-mcp"),
        "displayName": schema.get("displayName", schema.get("server", "Telegram MCP")),
        "description": schema.get("description", ""),
        "tabs": TELEGRAM_TABS,
    }
    return render_credential_form(
        render_schema,
        submit_url=submit_url,
        prefill=prefill,
        initial_tab=initial_tab,
    )
