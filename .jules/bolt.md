## 2025-05-15 - Refactoring long functions in credential_state.py
**Learning:** Large functions with distinct logic branches (like multi-user vs single-user) are hard to maintain and test. Splitting them into private helper functions improves readability and adheres to clean code principles.
**Action:** Always look for logical branch points in complex functions to extract them into well-named helper functions.
## 2025-05-15 - Further refactoring and test coverage for credential_state.py
**Learning:** Even after an initial refactor, functions can still be simplified by splitting them based on specific actions (e.g., OTP vs. Password). This lead to a much cleaner `on_step_submitted` implementation. Additionally, using `coverage` to identify and add missing tests ensures that critical paths like multi-user 2FA are fully verified.
**Action:** Aim for small, single-purpose functions even within internal helpers. Use coverage tools as a guide to ensure no critical logic branches are left untested.
