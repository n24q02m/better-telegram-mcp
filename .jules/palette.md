## 2024-06-25 - Improve ARIA associations in credential forms
**Learning:** For dynamic/conditionally-visible elements like status boxes or inline errors (e.g. `status-box`, `step-error`), it is completely safe and highly recommended to associate them proactively via `aria-describedby` directly on the `<input>` fields, even if the error blocks are initially empty or styled as `display: none`. Furthermore, strictly decorative strings like "Required" visual badges adjacent to natively `<input required>` fields should have `aria-hidden="true"` applied to avoid screen readers announcing "Required required" redundantly.
**Action:** Always verify if a native `required` attribute exists on inputs before adding visual "Required" text. If it does, ensure the visual text is masked with `aria-hidden="true"`. Pre-wire inputs to their respective alert/status `div` elements with `aria-describedby` during HTML templating.
## 2024-05-05 - Focus First Invalid Input on Form Validation Failure
**Learning:** Bringing focus to the first invalid input when client-side form validation fails is a low-effort, high-impact a11y/UX pattern that works natively without relying solely on screen reader ARIA live regions to announce errors.
**Action:** Always add `.focus()` calls when interrupting form submissions with JS validation logic.

## 2024-06-25 - Focus Management in Async Forms
**Learning:** In asynchronous form flows (e.g., fetch API calls in `credential_form.py`), failing to explicitly restore keyboard focus to the input field within error handling branches (like `.catch()` blocks) causes screen readers and keyboard users to lose their context upon network or validation failures. This creates a frustrating experience where users have to navigate back to the input to correct the issue.
**Action:** Always ensure that keyboard focus is returned to the relevant interactive element (e.g., `inputEl.focus();`) after an asynchronous operation fails and the UI is reset.

## 2024-07-28 - W3C ARIA Tablist Pattern Keyboard Navigation
**Learning:** For custom tabbed interfaces (like the Bot Mode / User Mode toggle), setting `role="tablist"` and `role="tab"` is not enough for complete accessibility. Users relying on keyboard navigation expect the W3C ARIA Tablist pattern, which specifically dictates that `Tab` moves focus *into* the active tab, and `ArrowLeft` / `ArrowRight` navigate *between* tabs. Without this keyboard event handling, custom tab arrays remain difficult or confusing to navigate for screen reader and keyboard-only users.
**Action:** When implementing custom tabs, always include a W3C-compliant roving `tabindex` (setting `tabindex="0"` on the active tab and `tabindex="-1"` on inactive tabs) and add `keydown` event listeners to handle `ArrowLeft` and `ArrowRight` keys for seamlessly shifting focus and selection between the tab buttons.

## 2024-07-28 - Contrast Requirements for Dark Themes
**Learning:** Text using color `#666` fails WCAG AA 4.5:1 contrast requirements when placed against dark-themed backgrounds such as `#1a1a1a`.
**Action:** When designing dark themes, ensure that subtle or secondary text elements (like `.server-id` and `.help-text`) are upgraded to at least `#888` or `#999` to maintain readability and accessibility standards.

## 2024-11-20 - Clear Error States on Input
**Learning:** In asynchronous forms or forms with client-side validation, error states (like visual `aria-invalid` styling or inline error messages) that linger even after the user begins typing to correct the issue create a frustrating experience. It forces the user to wonder if their new input is also invalid before they have even submitted it.
**Action:** Always attach `input` event listeners to form fields to actively strip validation styling (`aria-invalid`) and hide inline error messages as soon as the user resumes typing, preventing lingering error states.
