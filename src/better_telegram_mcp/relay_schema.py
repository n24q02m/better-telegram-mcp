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


# Opt in to the username-derived stable subject, so a returning user reaches the
# same per-``sub`` bucket instead of the random subject minted per ``/authorize``.
#
# This server supplies its own ``custom_credential_form_html``, and mcp-core's
# local OAuth app only passes ``include_username_field`` to its *default*
# renderer -- a custom renderer wins and never receives the flag. So the form
# side has to opt in here while ``server.py`` opts in on the transport side.
# Both read this one constant so they cannot drift apart.
STABLE_SUB_ENABLED = True

_SHAKE_ANIMATION_JS = """<script>
(function(){
var m = window.matchMedia("(prefers-reduced-motion: reduce)");
new MutationObserver(function(muts) {
    if(m.matches) return;
    muts.forEach(function(mut) {
        var el = mut.target;
        if(mut.attributeName === "aria-invalid" && el.getAttribute("aria-invalid") === "true" && el.classList.contains("field-input")) {
            el.animate([
                {transform:"translateX(0)"},{transform:"translateX(-4px)"},{transform:"translateX(4px)"},{transform:"translateX(-4px)"},{transform:"translateX(4px)"},{transform:"translateX(0)"}
            ], {duration: 400, easing: "ease-in-out"});
        }
    });
}).observe(document.body, {attributes: true, subtree: true, attributeFilter: ["aria-invalid"]});
})();
</script>"""


_PASSWORD_TOGGLE_JS = """<script>
(function(){
function attach(i) {
    if(i.dataset.hasToggle) return;
    i.dataset.hasToggle = "true";
    var d = document.createElement("div"); d.style.position = "relative";
    i.parentNode.insertBefore(d, i); d.appendChild(i);
    var b = document.createElement("button"); b.type = "button";
    b.style.cssText = "position:absolute; right:0.5rem; top:50%; transform:translateY(-50%); background:none; border:none; color:inherit; font-size:0.75rem; cursor:pointer; padding:0.25rem; font-weight:bold;";
    d.appendChild(b);
    var lf = i.dataset.field || "";
    var sync = function() {
        if((i.dataset.field || "") !== lf) {
            b.textContent = "SHOW"; b.setAttribute("aria-label", "Show password"); b.setAttribute("aria-pressed", "false");
            lf = i.dataset.field || "";
        }
        var isPwd = i.type === "password" || b.textContent === "HIDE";
        b.style.display = isPwd ? "block" : "none";
        i.style.paddingRight = isPwd ? "3.5rem" : "";
        b.disabled = i.disabled; b.style.opacity = i.disabled ? "0.5" : "1"; b.style.cursor = i.disabled ? "not-allowed" : "pointer";
        b.title = i.disabled ? "Disabled during submission" : (i.type === "password" ? "Show password" : "Hide password");
        if(i.type === "password" && b.textContent !== "SHOW") {
            b.textContent = "SHOW"; b.setAttribute("aria-label", "Show password"); b.setAttribute("aria-pressed", "false");
        }
    };
    sync();
    b.addEventListener("click", function() {
        var pwd = i.type === "password"; i.type = pwd ? "text" : "password";
        b.textContent = pwd ? "HIDE" : "SHOW"; b.setAttribute("aria-label", pwd ? "Hide password" : "Show password"); b.setAttribute("aria-pressed", pwd ? "true" : "false");
        b.title = pwd ? "Hide password" : "Show password";
    });
    new MutationObserver(sync).observe(i, {attributes: true, attributeFilter: ["disabled", "type", "data-field"]});
}
var botToken = document.getElementById("field-TELEGRAM_BOT_TOKEN");
if(botToken) attach(botToken);
new MutationObserver(function() {
    var stepInp = document.getElementById("step-input");
    if(stepInp) attach(stepInp);
}).observe(document.body, {childList: true, subtree: true});
})();
</script>"""


def render_telegram_form(
    schema: dict[str, Any],
    submit_url: str,
    prefill: dict[str, str] | None = None,
) -> str:
    """Render the Telegram credential form via mcp-core's tabbed renderer.

    Matches the ``custom_credential_form_html`` callback contract
    (``(schema, submit_url, *, prefill) -> html``) that ``run_http_server``
    invokes. The shared renderer owns field layout, tab switching, active-panel
    submit, OTP/2FA step chaining, and ``redirect_url`` follow. This Telegram
    wrapper adds the ``initial_tab`` hint: when the driver prefills a phone but
    no bot token (the ``telegram-user`` E2E case), open on the User tab so the
    user just clicks Connect instead of retyping the phone or pasting a bot
    token. Bot-only and dual prefill default to Bot. It also injects the
    attach-once password-toggle enhancement after the shared HTML is rendered.

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
    html = render_credential_form(
        render_schema,
        submit_url=submit_url,
        prefill=prefill,
        initial_tab=initial_tab,
        include_username_field=STABLE_SUB_ENABLED,
    )
    return html.replace("</body>", _PASSWORD_TOGGLE_JS + "\n" + _SHAKE_ANIMATION_JS + "\n</body>")
