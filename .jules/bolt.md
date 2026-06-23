
## 2025-05-14 - ModeError coverage and Task alignment
**Learning:** Task descriptions often provide specific error messages and exception types (like ValueError) that might differ from the current implementation. Aligning with these while maintaining backward compatibility and project-specific helpful hints (like user mode instructions) is key.
**Action:** Always verify if a custom exception should inherit from a standard one (like ValueError) to satisfy task constraints, and use simple logic to maintain 100% coverage without complex branch testing.
