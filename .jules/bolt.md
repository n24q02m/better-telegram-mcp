## 2026-06-23 - [Refactoring long functions]
**Learning:** Refactoring long functions into smaller, focused helpers improves readability and maintainability. In `src/better_telegram_mcp/transports/http.py`, splitting `_start_multi_user_http` into initialization, lifecycle, and execution blocks reduced complexity.
**Action:** Always monitor function length and extract logically distinct blocks into helper functions, especially when dealing with complex setup and lifecycle management.
