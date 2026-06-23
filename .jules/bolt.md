## 2025-05-14 - Refactoring Mega-Tools for Maintainability
**Learning:** Functions exceeding 100 lines (like the `config` tool) should be refactored into domain-specific handlers within dedicated modules (e.g., `tools/config_tool.py`). Using Pydantic models (e.g., `ConfigOptions`) for tool arguments ensures consistent type validation and cleaner signatures when delegating logic.
**Action:** Proactively split tool logic into smaller, action-specific handlers and use Pydantic models for argument passing to keep the main server module lean.
