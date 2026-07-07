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

## 2024-07-29 - Clear Validation State on Input
**Learning:** Lingering error states (`aria-invalid="true"` or visible error messages) are frustrating when users begin to correct the issue but the UI continues shouting at them until the next submit.
**Action:** Always attach `input` event listeners to form fields to actively strip validation styling and hide inline error messages as soon as the user resumes typing.
## 2024-05-19 - Password Visibility Toggles for API Keys
**Learning:** Password visibility toggles (Show/Hide buttons) are not just helpful for user passwords, but provide a critical UX improvement for long API keys (like Bot Tokens). Users often paste partial keys or experience issues verifying successful copy-pastes, leading to frustrating auth failures.
**Action:** Always consider adding "Show/Hide" toggle buttons to `type="password"` fields that accept long API keys or tokens to allow users to visually verify their input before submitting.

## 2024-07-30 - ARIA Pressed for State Toggles
**Learning:** State toggle buttons (like password visibility Show/Hide toggles) need to utilize the `aria-pressed` attribute to properly communicate their active state to screen readers.
**Action:** Ensure toggle buttons include `aria-pressed="false"` initially and dynamically update to `true` when activated.

## 2024-07-30 - Color Scheme Meta Tag for Dark Themes
**Learning:** Dark-themed HTML templates must explicitly include `<meta name="color-scheme" content="dark">` to ensure native browser elements (like scrollbars and autofill dropdowns) adapt to the dark aesthetic instead of defaulting to a jarring light mode.
**Action:** Always include the `<meta name="color-scheme" content="dark">` tag in the `<head>` of dark-themed HTML documents.

## 2024-07-29 - Enhancing State Change UX with Subtle Animations
**Learning:** Instantaneous layout shifts or state changes (e.g., switching between tabs or dynamically surfacing complex multi-step forms) can feel jarring or unpolished, potentially increasing cognitive load as users mentally trace the new UI structure. Subtle animations, such as a quick fade-in with a slight downward translation (`translateY`), soften these transitions, providing a much smoother, higher-quality interaction.
**Action:** Apply lightweight, short-duration CSS `@keyframes` animations (e.g., `<0.3s`) to significant DOM additions or view transitions, particularly when toggling `.active` panel states or appending new user prompts.

## 2026-06-21 - Prevent Hover Styles on Disabled Interactive Elements
**Learning:** Applying `:hover` styles universally to interactive elements like buttons and tabs creates confusing visual feedback when those elements are `disabled`. Users may interpret the hover effect as an indication that the element is clickable, leading to frustration.
**Action:** When styling `:hover` states, always use the `:not(:disabled):hover` pseudo-class (or equivalent) to ensure interactive styling is only applied to active elements. Additionally, explicitly style `:disabled` states (e.g. `opacity: 0.5; cursor: not-allowed;`) to make the disabled status visually unambiguous.

## 2026-06-21 - Prefer Native Labels over ARIA for Dynamic Prompts
**Learning:** Using a generic `<p>` tag combined with `aria-labelledby` on an input for dynamic forms (like multi-step OTP prompts) provides accessible names to screen readers but misses a key physical usability benefit. A semantic `<label>` properly associated with an input using the `for`/`id` relationship increases the clickable/tap area, allowing users to click the text prompt itself to focus the input field.
**Action:** When dynamically generating form elements in JavaScript, always prefer creating a `<label>` element and setting its `for` attribute to the input's `id` instead of relying on `aria-labelledby` with generic block elements.
## 2024-08-01 - Active States for Interactive Elements
**Learning:** Adding subtle `:active` pseudo-class styles with `transform: scale()` provides tactile visual feedback for interactive elements (like buttons and tabs), making the interface feel more responsive.
**Action:** When creating custom buttons or interactive tabs, define an `:active` state using `:not(:disabled):active` and apply a slight scale down (e.g., `transform: scale(0.98)`) and ensure `transform` is included in the element's `transition` property.
## 2024-08-05 - Reduced Motion Accessibility
**Learning:** Animations and transitions can be uncomfortable or inaccessible for users with vestibular disorders or motion sensitivities. Relying solely on CSS transitions and keyframes without respecting the operating system's reduced motion settings is a widespread accessibility failure.
**Action:** Always include a `@media (prefers-reduced-motion: reduce)` block in custom CSS to globally neutralize animations (e.g., setting `animation-duration: 0.01ms !important; transition-duration: 0.01ms !important;`) for environments where users have requested reduced motion.

## 2024-11-20 - Dual-Channel Validation Feedback
**Learning:** Relying solely on color (like `#f87171` red borders) for `aria-invalid` states is insufficient for users with color vision deficiencies and can be easily missed. Providing dual-channel feedback by combining color with a subtle, non-disruptive motion animation (like a short horizontal `@keyframes shake`) significantly improves error discoverability and accessibility.
**Action:** When implementing client-side validation, always apply a subtle motion animation (e.g., `shake 0.4s ease-in-out`) alongside color changes to `.field-input[aria-invalid="true"]` elements to provide robust, dual-channel error feedback, while ensuring it respects `prefers-reduced-motion: reduce`.
## 2024-05-19 - Use field-group and semantic labels for dynamic prompts
**Learning:** For dynamic form inputs (like OTP steps), ensure visual consistency and accessibility by wrapping the input and label in a `.field-group` container, applying the `.field-label` class to the semantic `<label>`, and explicitly appending `<span class="required-badge" aria-hidden="true">Required</span>` to mandatory fields instead of rendering prompts as title headers.
**Action:** Always maintain uniform visual hierarchy by matching the dynamic step form markup structure with the main form's styling pattern.

## 2024-10-21 - Disable Auxiliary Elements During Async Form Submission
**Learning:** UX/Accessibility Pattern: When transitioning a form into a loading or disabled state during async submissions, explicitly disable all associated auxiliary interactive elements (such as password visibility toggles) alongside the primary inputs and submit buttons to prevent inconsistent UI states.
**Action:** Always verify all interactive elements are disabled during form submits, including toggle buttons.
