"""Custom credential form for telegram: Bot Mode + User Mode tabs.

Renders a dark-themed HTML form matching mcp-core's default form style,
but with two tabs (Bot Mode / User Mode) so the user fills exactly one
credential set. Only the active tab's fields are submitted on POST.

User mode triggers multi-step auth via ``next_step`` (otp_required /
password_required). The step-input UI is identical to mcp-core's default
form (same ``showStepInput``/``submitStep`` behavior, same ``/otp`` endpoint
derivation) so the chained OTP flow works transparently.
"""

from __future__ import annotations

import html as html_module
from typing import Any


def _escape(value: Any) -> str:
    """Escape a value for safe HTML insertion."""
    return html_module.escape(str(value), quote=True)


def render_telegram_credential_form(
    schema: dict[str, Any],
    submit_url: str,
    prefill: dict[str, str] | None = None,
) -> str:
    """Render telegram credential form with Bot Mode + User Mode tabs.

    Args:
        schema: RelayConfigSchema dict (server / displayName / description).
        submit_url: URL the form POSTs to (includes authorize nonce).
        prefill: Optional ``{KEY: VALUE}`` mapping populated by mcp-core
            from ``?prefill_<KEY>=<VALUE>`` GET query params. Recognised
            keys: ``TELEGRAM_BOT_TOKEN``, ``TELEGRAM_PHONE``. When present,
            the matching input renders with ``value="..."`` and the form
            auto-activates the matching tab so the user just clicks
            Connect (skipping the retype step). Phone-only prefill (the
            telegram-user E2E case) opens on User Mode tab.

    Returns:
        Complete HTML document string. All dynamic content is HTML-escaped;
        JS dynamic content is inserted via ``textContent`` / ``setAttribute``
        to stay XSS-safe.
    """
    display_name = _escape(
        schema.get("displayName", schema.get("server", "Telegram MCP"))
    )
    server = _escape(schema.get("server", "better-telegram-mcp"))
    description = _escape(schema.get("description", ""))
    submit_url_escaped = _escape(submit_url)

    prefill = prefill or {}
    bot_token_value = _escape(prefill.get("TELEGRAM_BOT_TOKEN", ""))
    phone_value = _escape(prefill.get("TELEGRAM_PHONE", ""))
    bot_token_value_attr = f' value="{bot_token_value}"' if bot_token_value else ""
    phone_value_attr = f' value="{phone_value}"' if phone_value else ""

    # If phone is prefilled but bot token is not, the driver is exercising
    # User Mode (telegram-user E2E config) — open on the User tab so the
    # form does not invite the user to ignore the prefilled phone and
    # paste a bot token instead. Bot-only and dual-prefill default to Bot.
    initial_tab = "user" if phone_value and not bot_token_value else "bot"
    bot_tab_class = "tab active" if initial_tab == "bot" else "tab"
    user_tab_class = "tab active" if initial_tab == "user" else "tab"
    bot_tab_aria = "true" if initial_tab == "bot" else "false"
    user_tab_aria = "true" if initial_tab == "user" else "false"
    bot_panel_class = "tab-panel active" if initial_tab == "bot" else "tab-panel"
    user_panel_class = "tab-panel active" if initial_tab == "user" else "tab-panel"
    # ``required`` is set on the active panel's inputs only; the inactive
    # panel's required attr is removed so the form doesn't reject submits
    # because of a hidden field.
    bot_token_required = " required" if initial_tab == "bot" else ""
    phone_required = " required" if initial_tab == "user" else ""

    description_html = (
        f'<p class="server-description">{description}</p>' if description else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{display_name}</title>
    <style>
        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: #0f0f0f;
            color: #e8e8e8;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 15px;
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 2rem 1rem;
        }}

        .container {{
            width: 100%;
            max-width: 480px;
        }}

        .card {{
            background-color: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 1.25rem;
        }}

        .server-header {{
            margin-bottom: 1.5rem;
        }}

        .server-name {{
            font-size: 1.375rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 0.375rem;
        }}

        .server-id {{
            font-size: 0.8125rem;
            color: #666;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            margin-bottom: 0.5rem;
        }}

        .server-description {{
            font-size: 0.9rem;
            color: #999;
            margin-top: 0.5rem;
        }}

        .form-title {{
            font-size: 0.875rem;
            font-weight: 500;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 1.25rem;
        }}

        .tabs {{
            display: flex;
            gap: 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #2a2a2a;
        }}

        .tab {{
            flex: 1;
            padding: 0.75rem 1rem;
            background: transparent;
            border: none;
            color: #888;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            border-bottom: 2px solid transparent;
            transition: color 0.15s ease, border-color 0.15s ease;
            font-family: inherit;
        }}

        .tab:hover {{
            color: #ccc;
        }}

        .tab:focus-visible {{
            outline: 2px solid #4a6fa5;
            outline-offset: -2px;
            border-radius: 4px;
        }}

        .tab.active {{
            color: #fff;
            border-bottom-color: #4a6fa5;
        }}

        .tab:disabled {{
            cursor: not-allowed;
            opacity: 0.5;
        }}

        .tab-panel {{
            display: none;
        }}

        .tab-panel.active {{
            display: block;
        }}

        .field-group {{
            margin-bottom: 1.25rem;
        }}

        .field-label {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            font-weight: 500;
            color: #ccc;
            margin-bottom: 0.375rem;
        }}

        .required-badge {{
            font-size: 0.6875rem;
            font-weight: 500;
            color: #f87171;
            background-color: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.25);
            border-radius: 4px;
            padding: 0.1rem 0.4rem;
        }}

        .field-input {{
            width: 100%;
            background-color: #111;
            border: 1px solid #2e2e2e;
            border-radius: 8px;
            color: #e8e8e8;
            font-size: 0.9375rem;
            padding: 0.625rem 0.875rem;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
            outline: none;
            font-family: inherit;
        }}

        .field-input:focus {{
            border-color: #4a6fa5;
            box-shadow: 0 0 0 3px rgba(74, 111, 165, 0.2);
        }}

        .field-input[aria-invalid="true"] {{
            border-color: #f87171;
        }}

        .field-input[aria-invalid="true"]:focus {{
            border-color: #f87171;
            box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.2);
        }}

        .field-input::placeholder {{
            color: #555;
        }}

        .help-text {{
            font-size: 0.8125rem;
            color: #666;
            margin-top: 0.375rem;
        }}

        .help-text a {{
            color: #6c9bd2;
            text-decoration: none;
        }}

        .help-text a:hover {{
            text-decoration: underline;
        }}

        .help-text a:focus-visible {{
            outline: 2px solid #4a6fa5;
            outline-offset: 2px;
            border-radius: 2px;
        }}

        .submit-btn {{
            width: 100%;
            background-color: #4a6fa5;
            border: none;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            font-size: 0.9375rem;
            font-weight: 500;
            padding: 0.75rem 1.5rem;
            transition: background-color 0.15s ease, opacity 0.15s ease;
            margin-top: 0.5rem;
            font-family: inherit;
        }}

        .submit-btn:hover {{
            background-color: #5a7fb5;
        }}

        .submit-btn:focus-visible {{
            outline: 2px solid #4a6fa5;
            outline-offset: 2px;
        }}

        .submit-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .submit-btn[aria-busy="true"] {{
            color: transparent !important;
            position: relative;
            pointer-events: none;
            opacity: 1 !important;
            background-color: #4a6fa5 !important;
        }}

        .submit-btn[aria-busy="true"]::after {{
            content: "";
            position: absolute;
            left: 50%;
            top: 50%;
            width: 1.25rem;
            height: 1.25rem;
            margin: -0.625rem 0 0 -0.625rem;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: #fff;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg) }}
        }}

        .status-box {{
            display: none;
            border-radius: 8px;
            font-size: 0.875rem;
            margin-top: 1rem;
            padding: 0.75rem 1rem;
        }}

        .status-box.success {{
            background-color: rgba(52, 199, 89, 0.1);
            border: 1px solid rgba(52, 199, 89, 0.3);
            color: #34c759;
        }}

        .status-box.error {{
            background-color: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.3);
            color: #f87171;
        }}

        .status-box.info {{
            background-color: rgba(74, 111, 165, 0.1);
            border: 1px solid rgba(74, 111, 165, 0.3);
            color: #6c9bd2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="server-header">
                <h1 class="server-name">{display_name}</h1>
                <div class="server-id">{server}</div>
                {description_html}
            </div>

            <div class="tabs" role="tablist">
                <button type="button" id="tab-bot" class="{bot_tab_class}" data-tab="bot" role="tab" aria-selected="{bot_tab_aria}" aria-controls="panel-bot">Bot Mode</button>
                <button type="button" id="tab-user" class="{user_tab_class}" data-tab="user" role="tab" aria-selected="{user_tab_aria}" aria-controls="panel-user">User Mode</button>
            </div>

            <form id="credential-form" novalidate>
                <div id="panel-bot" class="{bot_panel_class}" data-panel="bot" role="tabpanel" aria-labelledby="tab-bot">
                    <div class="field-group">
                        <label for="field-TELEGRAM_BOT_TOKEN" class="field-label">
                            Bot Token
                            <span class="required-badge" aria-hidden="true">Required</span>
                        </label>
                        <input
                            id="field-TELEGRAM_BOT_TOKEN"
                            name="TELEGRAM_BOT_TOKEN"
                            type="password"
                            placeholder="123456:ABC-DEF..."
                            class="field-input"
                            autocomplete="off"
                            autocorrect="off"
                            autocapitalize="off"
                            spellcheck="false"{bot_token_value_attr}
                            aria-describedby="help-bot-token status-box"{bot_token_required}
                        />
                        <p id="help-bot-token" class="help-text">
                            <a href="https://core.telegram.org/bots#botfather" target="_blank" rel="noopener noreferrer">Get from @BotFather on Telegram</a>
                        </p>
                    </div>
                </div>

                <div id="panel-user" class="{user_panel_class}" data-panel="user" role="tabpanel" aria-labelledby="tab-user">
                    <div class="field-group">
                        <label for="field-TELEGRAM_PHONE" class="field-label">
                            Phone Number
                            <span class="required-badge" aria-hidden="true">Required</span>
                        </label>
                        <input
                            id="field-TELEGRAM_PHONE"
                            name="TELEGRAM_PHONE"
                            type="tel"
                            placeholder="+84..."
                            class="field-input"
                            autocomplete="off"
                            autocorrect="off"
                            autocapitalize="off"
                            spellcheck="false"{phone_value_attr}
                            aria-describedby="help-phone status-box"{phone_required}
                        />
                        <p id="help-phone" class="help-text">
                            Full account access via MTProto. API ID/Hash built-in. OTP verification required after submit.
                        </p>
                    </div>
                </div>

                <button type="submit" class="submit-btn" id="submit-btn">Connect</button>

                <div class="status-box" id="status-box" role="alert"></div>
            </form>
        </div>
    </div>

    <script>
        (function () {{
            var form = document.getElementById("credential-form");
            var submitBtn = document.getElementById("submit-btn");
            var statusBox = document.getElementById("status-box");
            var submitUrl = "{submit_url_escaped}";
            var activeTab = "{initial_tab}";

            // --- Tab switching -------------------------------------------------
            var tabs = document.querySelectorAll(".tab");
            tabs.forEach(function (tab) {{
                tab.addEventListener("click", function () {{
                    if (tab.disabled) {{
                        return;
                    }}
                    activeTab = tab.dataset.tab;
                    tabs.forEach(function (t) {{
                        t.classList.remove("active");
                        t.setAttribute("aria-selected", "false");
                    }});
                    tab.classList.add("active");
                    tab.setAttribute("aria-selected", "true");
                    document.querySelectorAll(".tab-panel").forEach(function (p) {{
                        p.classList.remove("active");
                    }});
                    var panel = document.querySelector('.tab-panel[data-panel="' + activeTab + '"]');
                    if (panel) {{
                        panel.classList.add("active");
                    }}
                    // Reset status on tab switch, clear validation styling on inactive fields.
                    statusBox.style.display = "none";
                    statusBox.textContent = "";
                    form.querySelectorAll(".field-input").forEach(function (i) {{
                        i.removeAttribute("aria-invalid");
                        i.removeAttribute("required");
                    }});
                    // Set required on the active panel's inputs
                    if (panel) {{
                        panel.querySelectorAll(".field-input").forEach(function (i) {{
                            i.setAttribute("required", "");
                        }});
                    }}
                }});
            }});

            // --- Status helpers ------------------------------------------------
            function showStatus(type, message) {{
                statusBox.className = "status-box " + type;
                statusBox.textContent = message;
                statusBox.style.display = "block";
            }}

            // Derive /otp endpoint URL from submitUrl (replaces /authorize... with /otp).
            function otpUrl() {{
                return submitUrl.replace(/\\/authorize.*/, "/otp");
            }}

            // Stashed from initial POST /authorize response so OTP/password
            // completion can follow the OAuth redirect (external test harness,
            // Claude CLI, desktop app). Without this the form stalls on "close
            // tab" and external clients wait on a callback that never fires.
            var pendingRedirectUrl = null;

            // --- Step-input UI (otp_required / password_required) -------------
            // Identical behavior to mcp-core's default credential form:
            // builds/updates a step container, POSTs to /otp, chains next_step.
            function showStepInput(ns) {{
                // Hide the original credential form + tabs after first transition.
                if (form && form.style.display !== "none") {{
                    form.style.display = "none";
                }}
                var tabsEl = document.querySelector(".tabs");
                if (tabsEl) {{
                    tabsEl.style.display = "none";
                }}

                var container = document.getElementById("step-container");
                var promptEl, inputEl, buttonEl, errorEl;
                if (container) {{
                    promptEl = document.getElementById("step-prompt");
                    inputEl = document.getElementById("step-input");
                    buttonEl = document.getElementById("step-submit");
                    errorEl = document.getElementById("step-error");
                    errorEl.style.display = "none";
                    errorEl.textContent = "";
                    inputEl.value = "";
                    inputEl.disabled = false;
                    buttonEl.disabled = false;
                    buttonEl.removeAttribute("aria-busy");
                    buttonEl.textContent = "Verify";
                }} else {{
                    var card = form.parentNode;
                    container = document.createElement("div");
                    container.id = "step-container";

                    promptEl = document.createElement("p");
                    promptEl.id = "step-prompt";
                    promptEl.className = "form-title";
                    container.appendChild(promptEl);

                    var fieldGroup = document.createElement("div");
                    fieldGroup.className = "field-group";
                    inputEl = document.createElement("input");
                    inputEl.id = "step-input";
                    inputEl.className = "field-input";
                    inputEl.setAttribute("autocomplete", "off");
                    inputEl.setAttribute("autocorrect", "off");
                    inputEl.setAttribute("autocapitalize", "off");
                    inputEl.setAttribute("spellcheck", "false");
                    inputEl.setAttribute("aria-labelledby", "step-prompt");
                    inputEl.setAttribute("aria-describedby", "step-error");
                    fieldGroup.appendChild(inputEl);
                    container.appendChild(fieldGroup);

                    buttonEl = document.createElement("button");
                    buttonEl.type = "button";
                    buttonEl.id = "step-submit";
                    buttonEl.className = "submit-btn";
                    buttonEl.textContent = "Verify";
                    container.appendChild(buttonEl);

                    errorEl = document.createElement("div");
                    errorEl.id = "step-error";
                    errorEl.className = "status-box error";
                    errorEl.setAttribute("role", "alert");
                    errorEl.style.display = "none";
                    container.appendChild(errorEl);

                    card.appendChild(container);

                    buttonEl.addEventListener("click", function () {{
                        submitStep();
                    }});
                    inputEl.addEventListener("keydown", function (evt) {{
                        if (evt.key === "Enter") {{
                            evt.preventDefault();
                            submitStep();
                        }}
                    }});
                }}

                promptEl.textContent = ns.text || "";
                inputEl.setAttribute("type", ns.input_type || "text");
                inputEl.setAttribute("placeholder", ns.placeholder || "");
                inputEl.dataset.field = ns.field || "value";
                inputEl.focus();
            }}

            function submitStep() {{
                var inputEl = document.getElementById("step-input");
                var buttonEl = document.getElementById("step-submit");
                var errorEl = document.getElementById("step-error");
                var fieldName = inputEl.dataset.field || "value";
                var value = inputEl.value;
                if (value.trim() === "") {{
                    errorEl.textContent = "Please enter a value.";
                    errorEl.style.display = "block";
                    inputEl.setAttribute("aria-invalid", "true");
                    inputEl.focus();
                    return;
                }}
                errorEl.style.display = "none";
                errorEl.textContent = "";
                inputEl.removeAttribute("aria-invalid");
                buttonEl.disabled = true;
                buttonEl.setAttribute("aria-busy", "true");
                buttonEl.textContent = "Verifying...";
                inputEl.disabled = true;

                var body = {{}};
                body[fieldName] = value;

                fetch(otpUrl(), {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify(body),
                }})
                    .then(function (response) {{
                        return response.json().then(function (data) {{
                            if (data.ok) {{
                                if (data.next_step && (data.next_step.type === "otp_required" || data.next_step.type === "password_required")) {{
                                    showStepInput(data.next_step);
                                }} else {{
                                    var container = document.getElementById("step-container");
                                    while (container.firstChild) {{
                                        container.removeChild(container.firstChild);
                                    }}
                                    var done = document.createElement("div");
                                    done.className = "status-box success";
                                    done.style.display = "block";
                                    if (typeof pendingRedirectUrl === "string" && pendingRedirectUrl.length > 0) {{
                                        done.textContent = "Setup complete! Redirecting...";
                                        container.appendChild(done);
                                        window.location.replace(pendingRedirectUrl);
                                    }} else {{
                                        done.textContent = "Setup complete! You can close this tab.";
                                        container.appendChild(done);
                                    }}
                                }}
                            }} else {{
                                errorEl.textContent = data.error || data.error_description || "Verification failed.";
                                errorEl.style.display = "block";
                                inputEl.disabled = false;
                                inputEl.setAttribute("aria-invalid", "true");
                                buttonEl.disabled = false;
                                buttonEl.removeAttribute("aria-busy");
                                buttonEl.textContent = "Verify";
                                inputEl.focus();
                            }}
                        }});
                    }})
                    .catch(function (err) {{
                        errorEl.textContent = "Network error: " + err.message;
                        errorEl.style.display = "block";
                        inputEl.disabled = false;
                        inputEl.setAttribute("aria-invalid", "true");
                        buttonEl.disabled = false;
                        buttonEl.removeAttribute("aria-busy");
                        buttonEl.textContent = "Verify";
                    }});
            }}

            // --- Form submit ---------------------------------------------------
            form.addEventListener("submit", function (event) {{
                event.preventDefault();

                // Collect ONLY the active tab panel's fields — the other mode's
                // fields are intentionally not sent so callback sees only chosen
                // mode's values.
                var activePanel = document.querySelector('.tab-panel.active');
                var inputs = activePanel ? activePanel.querySelectorAll('.field-input') : [];
                var payload = {{}};
                var valid = true;
                var firstInvalidInput = null;

                inputs.forEach(function (input) {{
                    if (input.value.trim() === "") {{
                        valid = false;
                        input.setAttribute("aria-invalid", "true");
                        if (!firstInvalidInput) {{
                            firstInvalidInput = input;
                        }}
                    }} else {{
                        input.removeAttribute("aria-invalid");
                        payload[input.name] = input.value;
                    }}
                }});

                if (!valid) {{
                    showStatus("error", "Please fill in the required field.");
                    if (firstInvalidInput) {{
                        firstInvalidInput.focus();
                    }}
                    return;
                }}

                submitBtn.disabled = true;
                submitBtn.setAttribute("aria-busy", "true");
                submitBtn.textContent = "Connecting...";
                statusBox.style.display = "none";

                fetch(submitUrl, {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify(payload),
                }})
                    .then(function (response) {{
                        return response.json().then(function (data) {{
                            if (data.ok) {{
                                // Stash the OAuth redirect target so follow-up async steps
                                // (OTP verify, 2FA password) can navigate to it on final
                                // success instead of orphaning the external client callback.
                                if (typeof data.redirect_url === "string" && data.redirect_url.length > 0) {{
                                    pendingRedirectUrl = data.redirect_url;
                                }}
                                if (data.next_step && (data.next_step.type === "otp_required" || data.next_step.type === "password_required")) {{
                                    statusBox.style.display = "none";
                                    showStepInput(data.next_step);
                                }} else if (data.next_step && data.next_step.type === "info") {{
                                    form.querySelectorAll(".field-input").forEach(function (i) {{ i.disabled = true; }});
                                    submitBtn.disabled = true;
                                    submitBtn.removeAttribute("aria-busy");
                                    submitBtn.textContent = "Connected";
                                    tabs.forEach(function (t) {{ t.disabled = true; }});
                                    showStatus("success", data.next_step.message || "Setup saved. Additional steps may be required.");
                                }} else if (pendingRedirectUrl) {{
                                    // No interactive next step — follow the OAuth redirect now
                                    // so the external client callback receives the auth code.
                                    form.querySelectorAll(".field-input").forEach(function (i) {{ i.disabled = true; }});
                                    submitBtn.disabled = true;
                                    submitBtn.removeAttribute("aria-busy");
                                    submitBtn.textContent = "Connected";
                                    tabs.forEach(function (t) {{ t.disabled = true; }});
                                    showStatus("success", "Credentials saved. Redirecting...");
                                    window.location.replace(pendingRedirectUrl);
                                }} else {{
                                    form.querySelectorAll(".field-input").forEach(function (i) {{ i.disabled = true; }});
                                    submitBtn.disabled = true;
                                    submitBtn.removeAttribute("aria-busy");
                                    submitBtn.textContent = "Connected";
                                    tabs.forEach(function (t) {{ t.disabled = true; }});
                                    var successMsg = data.message || "Connected successfully. You can close this window.";
                                    showStatus("success", successMsg);
                                }}
                            }} else {{
                                showStatus("error", data.error || data.error_description || "Request failed.");
                                submitBtn.disabled = false;
                                submitBtn.removeAttribute("aria-busy");
                                submitBtn.textContent = "Connect";
                            }}
                        }});
                    }})
                    .catch(function (err) {{
                        showStatus("error", "Network error: " + err.message);
                        submitBtn.disabled = false;
                        submitBtn.removeAttribute("aria-busy");
                        submitBtn.textContent = "Connect";
                    }});
            }});
        }})();
    </script>
</body>
</html>"""
