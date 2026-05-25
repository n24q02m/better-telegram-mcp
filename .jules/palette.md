## 2024-06-25 - Improve ARIA associations in credential forms
**Learning:** For dynamic/conditionally-visible elements like status boxes or inline errors (e.g. `status-box`, `step-error`), it is completely safe and highly recommended to associate them proactively via `aria-describedby` directly on the `<input>` fields, even if the error blocks are initially empty or styled as `display: none`. Furthermore, strictly decorative strings like "Required" visual badges adjacent to natively `<input required>` fields should have `aria-hidden="true"` applied to avoid screen readers announcing "Required required" redundantly.
**Action:** Always verify if a native `required` attribute exists on inputs before adding visual "Required" text. If it does, ensure the visual text is masked with `aria-hidden="true"`. Pre-wire inputs to their respective alert/status `div` elements with `aria-describedby` during HTML templating.
## 2024-05-05 - Focus First Invalid Input on Form Validation Failure
**Learning:** Bringing focus to the first invalid input when client-side form validation fails is a low-effort, high-impact a11y/UX pattern that works natively without relying solely on screen reader ARIA live regions to announce errors.
**Action:** Always add `.focus()` calls when interrupting form submissions with JS validation logic.

## 2024-06-25 - Focus Management in Async Forms
**Learning:** In asynchronous form flows (e.g., fetch API calls in `credential_form.py`), failing to explicitly restore keyboard focus to the input field within error handling branches (like `.catch()` blocks) causes screen readers and keyboard users to lose their context upon network or validation failures. This creates a frustrating experience where users have to navigate back to the input to correct the issue.
**Action:** Always ensure that keyboard focus is returned to the relevant interactive element (e.g., `inputEl.focus();`) after an asynchronous operation fails and the UI is reset.
