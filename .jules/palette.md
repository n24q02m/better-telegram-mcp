## 2026-05-08 - Dynamic Required Attribute Sync
**Learning:** For dynamic forms that toggle input visibility (like tabs), adding and removing the HTML `required` attribute solves native validation, but managing the `aria-required` attribute simultaneously ensures screen readers maintain correct state regardless of browser heuristics.
**Action:** When dynamically toggling HTML5 `required` properties using JavaScript, explicitly pair the changes with `aria-required="true"` or removing the attribute to guarantee accessibility consistency.
