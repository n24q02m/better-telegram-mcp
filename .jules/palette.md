## 2024-04-10 - Native Form Submission & Accessibility

**Learning:** When building inline HTML apps, relying on custom JavaScript `keydown` listeners for 'Enter' key submission breaks expected browser behavior and accessibility norms. Furthermore, performing async actions (like authentication) without disabling inputs can lead to race conditions or duplicate submissions from users double-clicking.
**Action:** Always wrap interactive input groups in semantic `<form>` elements and use `onsubmit` handlers with `event.preventDefault()`. This naturally supports 'Enter' key submission. Ensure `aria-busy` is set, a loading indicator is visually shown, and all form inputs are temporarily disabled during async requests to provide immediate, accessible feedback and prevent concurrent submissions.
