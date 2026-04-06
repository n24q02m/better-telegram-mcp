## 2026-04-06 - ARIA roles for dynamic status updates
**Learning:** Dynamic status messages and error divs in web templates must include `role=\"status\"` and `aria-live=\"polite\"` to ensure screen readers announce asynchronous updates to visually impaired users.
**Action:** Add `role=\"status\"` and `aria-live=\"polite\"` to all dynamic status and error elements.
