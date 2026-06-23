"""Custom credential form for telegram: Bot Mode + User Mode tabs.

Renders a dark-themed HTML form matching mcp-core's default form style,
but with two tabs (Bot Mode / User Mode) so the user fills exactly one
credential set. Only the active tab's fields are submitted on POST.

User mode triggers multi-step auth via ``next_step`` (otp_required /
password_required). The step-input UI is identical to mcp-core's default
form (same ``showStepInput``/``submitStep`` behavior, same ``/otp`` endpoint
derivation) so the chained OTP flow works transparently.
"""

import html as html_module
from typing import Any


def _escape(value: Any) -> str:
    """Escape a value for safe HTML insertion."""
    return html_module.escape(str(value), quote=True)


def _render_styles() -> str:
    """Render the CSS styles for the credential form."""
    return """<style>
        *, *::before, *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
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
        }

        .container {
            width: 100%;
            max-width: 480px;
        }

        .card {
            background-color: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 1.25rem;
        }

        .server-header {
            margin-bottom: 1.5rem;
        }

        .server-name {
            font-size: 1.375rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 0.375rem;
        }

        .server-id {
            font-size: 0.8125rem;
            color: #999;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            margin-bottom: 0.5rem;
        }

        .server-description {
            font-size: 0.9rem;
            color: #999;
            margin-top: 0.5rem;
        }

        .form-title {
            font-size: 0.875rem;
            font-weight: 500;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 1.25rem;
        }

        .tabs {
            display: flex;
            gap: 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #2a2a2a;
        }

        .tab {
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
        }

        .tab:not(:disabled):hover {
            color: #ccc;
        }

        .tab:focus-visible {
            outline: 2px solid #4a6fa5;
            outline-offset: -2px;
            border-radius: 4px;
        }

        .tab.active {
            color: #fff;
            border-bottom-color: #4a6fa5;
        }

        .tab:disabled {
            cursor: not-allowed;
            opacity: 0.5;
        }

        .tab-panel {
            display: none;
        }

        @keyframes fadeSlideDown {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .tab-panel.active {
            display: block;
            animation: fadeSlideDown 0.3s ease-out forwards;
        }

        #step-container {
            animation: fadeSlideDown 0.3s ease-out forwards;
        }

        .field-group {
            margin-bottom: 1.25rem;
        }

        .field-label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            font-weight: 500;
            color: #ccc;
            margin-bottom: 0.375rem;
            cursor: pointer;
        }

        .required-badge {
            font-size: 0.6875rem;
            font-weight: 500;
            color: #f87171;
            background-color: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.25);
            border-radius: 4px;
            padding: 0.1rem 0.4rem;
        }

        .password-wrapper {
            position: relative;
            display: flex;
            align-items: center;
        }

        .password-toggle {
            position: absolute;
            right: 0.75rem;
            background: transparent;
            border: none;
            color: #888;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            transition: color 0.15s ease, background-color 0.15s ease;
            font-family: inherit;
        }

        .password-toggle:not(:disabled):hover {
            color: #ccc;
            background-color: rgba(255, 255, 255, 0.05);
        }

        .password-toggle:disabled {
            cursor: not-allowed;
            opacity: 0.5;
        }

        .password-toggle:focus-visible {
            outline: 2px solid #4a6fa5;
            outline-offset: -2px;
            color: #fff;
        }

        .field-input {
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
        }

        .password-wrapper .field-input {
            padding-right: 4rem; /* Make room for the toggle button */
        }

        .field-input:focus {
            border-color: #4a6fa5;
            box-shadow: 0 0 0 3px rgba(74, 111, 165, 0.2);
        }

        .field-input[aria-invalid="true"] {
            border-color: #f87171;
        }

        .submit-btn {
            width: 100%;
            background-color: #4a6fa5;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            padding: 0.75rem;
            cursor: pointer;
            transition: background-color 0.15s ease, transform 0.1s active;
            font-family: inherit;
        }

        .submit-btn:not(:disabled):hover {
            background-color: #5a7fb5;
        }

        .submit-btn:not(:disabled):active {
            transform: scale(0.98);
        }

        .submit-btn:disabled {
            background-color: #2a2a2a;
            color: #666;
            cursor: not-allowed;
        }

        .help-text {
            font-size: 0.8125rem;
            color: #777;
            margin-top: 0.5rem;
        }

        .help-text a {
            color: #4a6fa5;
            text-decoration: none;
        }

        .help-text a:hover {
            text-decoration: underline;
        }

        .status-box {
            display: none;
            border-radius: 8px;
            font-size: 0.875rem;
            margin-top: 1rem;
            padding: 0.75rem 1rem;
        }

        .status-box.success {
            background-color: rgba(52, 199, 89, 0.1);
            border: 1px solid rgba(52, 199, 89, 0.3);
            color: #34c759;
        }

        .status-box.error {
            background-color: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.3);
            color: #f87171;
        }

        .status-box.info {
            background-color: rgba(74, 111, 165, 0.1);
            border: 1px solid rgba(74, 111, 165, 0.3);
            color: #6c9bd2;
        }
    </style>"""


def _render_header(display_name: str, server: str, description_html: str) -> str:
    """Render the server header section."""
    return f"""<div class="server-header">
                <h1 class="server-name">{display_name}</h1>
                <div class="server-id">{server}</div>
                {description_html}
            </div>"""


def _render_tabs(
    bot_tab_class: str,
    user_tab_class: str,
    bot_tab_aria: str,
    user_tab_aria: str,
    bot_tab_tabindex: str,
    user_tab_tabindex: str,
) -> str:
    """Render the tab navigation buttons."""
    return f"""<div class="tabs" role="tablist">
                <button type="button" id="tab-bot" class="{bot_tab_class}" data-tab="bot" role="tab" aria-selected="{bot_tab_aria}" tabindex="{bot_tab_tabindex}" aria-controls="panel-bot">Bot Mode</button>
                <button type="button" id="tab-user" class="{user_tab_class}" data-tab="user" role="tab" aria-selected="{user_tab_aria}" tabindex="{user_tab_tabindex}" aria-controls="panel-user">User Mode</button>
            </div>"""


def _render_form_panels(
    bot_panel_class: str,
    user_panel_class: str,
    bot_token_value_attr: str,
    bot_token_required: str,
    phone_value_attr: str,
    phone_required: str,
) -> str:
    """Render the credential input panels for Bot and User modes."""
    return f"""<div id="panel-bot" class="{bot_panel_class}" data-panel="bot" role="tabpanel" aria-labelledby="tab-bot">
                    <div class="field-group">
                        <label for="field-TELEGRAM_BOT_TOKEN" class="field-label">
                            Bot Token
                            <span class="required-badge" aria-hidden="true">Required</span>
                        </label>
                        <div class="password-wrapper">
                            <input
                                id="field-TELEGRAM_BOT_TOKEN"
                                name="TELEGRAM_BOT_TOKEN"
                                type="password"
                                placeholder="123456:ABC-DEF..."
                                class="field-input"
                                autocomplete="current-password"
                                autocorrect="off"
                                autocapitalize="off"
                                spellcheck="false"
                                inputmode="text"{bot_token_value_attr}
                                aria-describedby="help-bot-token status-box"{bot_token_required}
                            />
                            <button type="button" class="password-toggle" id="toggle-bot-token" aria-label="Show bot token" aria-controls="field-TELEGRAM_BOT_TOKEN" aria-pressed="false">Show</button>
                        </div>
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
                            autocomplete="tel"
                            inputmode="tel"
                            autocorrect="off"
                            autocapitalize="off"
                            spellcheck="false"{phone_value_attr}
                            aria-describedby="help-phone status-box"{phone_required}
                        />
                        <p id="help-phone" class="help-text">
                            Full account access via MTProto. API ID/Hash built-in. OTP verification required after submit.
                        </p>
                    </div>
                </div>"""


def _render_scripts(submit_url_escaped: str, initial_tab: str) -> str:
    """Render the client-side JavaScript logic."""
    return f"""<script>
        (function () {{
            var form = document.getElementById("credential-form");
            var submitBtn = document.getElementById("submit-btn");
            var statusBox = document.getElementById("status-box");
            var submitUrl = "{submit_url_escaped}";
            var activeTab = "{initial_tab}";

            // --- Password Visibility Toggle ------------------------------------
            function setupPasswordToggle(inputEl, toggleBtn, labelBase) {{
                if (!inputEl || !toggleBtn) return;
                toggleBtn.addEventListener("click", function () {{
                    if (inputEl.type === "password") {{
                        inputEl.type = "text";
                        toggleBtn.textContent = "Hide";
                        toggleBtn.setAttribute("aria-label", "Hide " + labelBase);
                        toggleBtn.setAttribute("aria-pressed", "true");
                    }} else {{
                        inputEl.type = "password";
                        toggleBtn.textContent = "Show";
                        toggleBtn.setAttribute("aria-label", "Show " + labelBase);
                        toggleBtn.setAttribute("aria-pressed", "false");
                    }}
                }});
            }}

            var botTokenInput = document.getElementById("field-TELEGRAM_BOT_TOKEN");
            var botTokenToggle = document.getElementById("toggle-bot-token");
            setupPasswordToggle(botTokenInput, botTokenToggle, "bot token");

            // --- Tab switching -------------------------------------------------
            var tabs = document.querySelectorAll(".tab");
            var tabsArray = Array.prototype.slice.call(tabs);

            // Clear errors when typing
            form.querySelectorAll(".field-input").forEach(function (input) {{
                input.addEventListener("input", function () {{
                    if (input.getAttribute("aria-invalid") === "true") {{
                        input.removeAttribute("aria-invalid");
                        statusBox.style.display = "none";
                        statusBox.textContent = "";
                    }}
                }});
            }});

            tabs.forEach(function (tab, index) {{
                tab.addEventListener("click", function () {{
                    if (tab.disabled) {{
                        return;
                    }}
                    activeTab = tab.dataset.tab;
                    tabs.forEach(function (t) {{
                        t.classList.remove("active");
                        t.setAttribute("aria-selected", "false");
                        t.setAttribute("tabindex", "-1");
                    }});
                    tab.classList.add("active");
                    tab.setAttribute("aria-selected", "true");
                    tab.setAttribute("tabindex", "0");
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

                // Keyboard navigation for W3C ARIA tablist pattern
                tab.addEventListener("keydown", function(e) {{
                    var targetIndex = -1;
                    if (e.key === "ArrowRight") {{
                        targetIndex = index + 1;
                        if (targetIndex >= tabsArray.length) targetIndex = 0;
                    }} else if (e.key === "ArrowLeft") {{
                        targetIndex = index - 1;
                        if (targetIndex < 0) targetIndex = tabsArray.length - 1;
                    }}

                    if (targetIndex !== -1) {{
                        e.preventDefault();
                        tabsArray[targetIndex].focus();
                        tabsArray[targetIndex].click();
                    }}
                }});
            }});

            // --- Status helpers ------------------------------------------------
            function showStatus(type, message) {{
                statusBox.className = "status-box " + type;
                if (type === "error") {{
                    statusBox.setAttribute("role", "alert");
                }} else {{
                    statusBox.setAttribute("role", "status");
                    statusBox.setAttribute("aria-live", "polite");
                }}
                statusBox.textContent = message;
                statusBox.style.display = "block";
            }}

            // --- OTP / Password chained input ----------------------------------
            var pendingRedirectUrl = null;

            function showStepInput(step) {{
                var container = document.getElementById("panel-" + activeTab);
                if (!container) return;

                // Hide original fields and title
                container.querySelectorAll(".field-group").forEach(function (el) {{ el.style.display = "none"; }});
                submitBtn.style.display = "none";

                var stepDiv = document.createElement("div");
                stepDiv.id = "step-container";
                stepDiv.className = "field-group";

                var label = document.createElement("label");
                label.className = "field-label";
                label.setAttribute("for", "step-input");
                label.textContent = step.message || "Verification Required";

                var inputWrapper = document.createElement("div");
                inputWrapper.className = "password-wrapper";

                var inputEl = document.createElement("input");
                inputEl.id = "step-input";
                inputEl.className = "field-input";
                inputEl.required = true;

                if (step.type === "otp_required") {{
                    inputEl.type = "text";
                    inputEl.placeholder = "Enter code";
                    inputEl.setAttribute("autocomplete", "one-time-code");
                    inputEl.setAttribute("inputmode", "numeric");
                }} else {{
                    inputEl.type = "password";
                    inputEl.placeholder = "Enter password";
                    inputEl.setAttribute("autocomplete", "current-password");
                }}

                var verifyBtn = document.createElement("button");
                verifyBtn.type = "button";
                verifyBtn.className = "submit-btn";
                verifyBtn.style.marginTop = "1rem";
                verifyBtn.textContent = "Verify";

                var errorEl = document.createElement("div");
                errorEl.className = "status-box error";
                errorEl.style.marginTop = "1rem";

                inputWrapper.appendChild(inputEl);
                stepDiv.appendChild(label);
                stepDiv.appendChild(inputWrapper);
                stepDiv.appendChild(verifyBtn);
                stepDiv.appendChild(errorEl);
                container.appendChild(stepDiv);

                inputEl.focus();

                // Clear error on type
                inputEl.addEventListener("input", function () {{
                    errorEl.style.display = "none";
                    inputEl.removeAttribute("aria-invalid");
                }});

                verifyBtn.addEventListener("click", function () {{
                    if (inputEl.value.trim() === "") {{
                        inputEl.setAttribute("aria-invalid", "true");
                        return;
                    }}
                    submitStep(step, inputEl.value, verifyBtn, inputEl, errorEl);
                }});

                inputEl.addEventListener("keydown", function (e) {{
                    if (e.key === "Enter") {{
                        e.preventDefault();
                        verifyBtn.click();
                    }}
                }});
            }}

            function submitStep(step, value, buttonEl, inputEl, errorEl) {{
                buttonEl.disabled = true;
                buttonEl.setAttribute("aria-busy", "true");
                buttonEl.textContent = "Verifying...";
                inputEl.disabled = true;

                // Relay maps step handling to ``/otp`` relative to the nonce authorize URL
                var otpUrl = submitUrl.replace(/\\/authorize\\?/, "/otp?");

                fetch(otpUrl, {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ value: value }}),
                }})
                    .then(function (response) {{
                        return response.json().then(function (data) {{
                            if (data.ok) {{
                                if (data.next_step) {{
                                    // Chain to next step (e.g. OTP -> Password)
                                    var oldStep = document.getElementById("step-container");
                                    if (oldStep) oldStep.remove();
                                    showStepInput(data.next_step);
                                }} else {{
                                    // Success!
                                    var container = document.querySelector(".container");
                                    while (container.firstChild) {{
                                        container.removeChild(container.firstChild);
                                    }}
                                    var done = document.createElement("div");
                                    done.className = "status-box success";
                                    done.setAttribute("role", "status");
                                    done.setAttribute("aria-live", "polite");
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
                        inputEl.focus();
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
                form.querySelectorAll(".field-input").forEach(function (i) {{ i.disabled = true; }});
                tabs.forEach(function (t) {{ t.disabled = true; }});

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
                                form.querySelectorAll(".field-input").forEach(function (i) {{ i.disabled = false; }});
                                tabs.forEach(function (t) {{ t.disabled = false; }});

                                // Restore focus to the first visible input field so users can immediately correct it
                                var activePanel = document.querySelector('.tab-panel.active');
                                if (activePanel) {{
                                    var firstInput = activePanel.querySelector('.field-input');
                                    if (firstInput) {{
                                        firstInput.focus();
                                    }}
                                }}
                            }}
                        }});
                    }})
                    .catch(function (err) {{
                        showStatus("error", "Network error: " + err.message);
                        submitBtn.disabled = false;
                        submitBtn.removeAttribute("aria-busy");
                        submitBtn.textContent = "Connect";
                        form.querySelectorAll(".field-input").forEach(function (i) {{ i.disabled = false; }});
                        tabs.forEach(function (t) {{ t.disabled = false; }});

                        // Restore focus to the first visible input field so users can immediately correct it
                        var activePanel = document.querySelector('.tab-panel.active');
                        if (activePanel) {{
                            var firstInput = activePanel.querySelector('.field-input');
                            if (firstInput) {{
                                firstInput.focus();
                            }}
                        }}
                    }});
            }});
        }})();
    </script>"""


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

    initial_tab = "user" if phone_value and not bot_token_value else "bot"
    bot_tab_class = "tab active" if initial_tab == "bot" else "tab"
    user_tab_class = "tab active" if initial_tab == "user" else "tab"
    bot_tab_aria = "true" if initial_tab == "bot" else "false"
    user_tab_aria = "true" if initial_tab == "user" else "false"
    bot_tab_tabindex = "0" if initial_tab == "bot" else "-1"
    user_tab_tabindex = "0" if initial_tab == "user" else "-1"
    bot_panel_class = "tab-panel active" if initial_tab == "bot" else "tab-panel"
    user_panel_class = "tab-panel active" if initial_tab == "user" else "tab-panel"
    bot_token_required = " required" if initial_tab == "bot" else ""
    phone_required = " required" if initial_tab == "user" else ""

    description_html = (
        f'<p class="server-description">{description}</p>' if description else ""
    )

    styles_html = _render_styles()
    header_html = _render_header(display_name, server, description_html)
    tabs_html = _render_tabs(
        bot_tab_class,
        user_tab_class,
        bot_tab_aria,
        user_tab_aria,
        bot_tab_tabindex,
        user_tab_tabindex,
    )
    panels_html = _render_form_panels(
        bot_panel_class,
        user_panel_class,
        bot_token_value_attr,
        bot_token_required,
        phone_value_attr,
        phone_required,
    )
    scripts_html = _render_scripts(submit_url_escaped, initial_tab)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="color-scheme" content="dark">
    <title>{display_name}</title>
    {styles_html}
</head>
<body>
    <div class="container">
        <div class="card">
            {header_html}
            {tabs_html}
            <form id="credential-form" novalidate>
                {panels_html}
                <button type="submit" class="submit-btn" id="submit-btn">Connect</button>
                <div class="status-box" id="status-box" role="alert"></div>
            </form>
        </div>
    </div>
    {scripts_html}
</body>
</html>"""
