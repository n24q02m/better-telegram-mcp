## 2024-05-24 - Added Autocomplete to Telegram Credential Form
**Learning:** Using generic `autocomplete="off"` for auth forms harms mobile usability. Using standard browser hints like `autocomplete="tel"`, `autocomplete="one-time-code"`, and `autocomplete="current-password"` significantly improves the login experience by enabling browser-native autofill.
**Action:** When creating forms, particularly for credential entry and multi-step OTP flows, dynamically map the server-provided `ns.type` to specific browser `autocomplete` strings.
