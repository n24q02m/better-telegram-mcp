## 2025-05-15 - Refactoring long functions in credential_state.py
**Learning:** Large functions with distinct logic branches (like multi-user vs single-user) are hard to maintain and test. Splitting them into private helper functions improves readability and adheres to clean code principles.
**Action:** Always look for logical branch points in complex functions to extract them into well-named helper functions.
