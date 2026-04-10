## 2025-04-10 - Cached Documentation Loading
**Learning:** For static content like documentation, optimize repeated I/O by wrapping synchronous file operations in a function decorated with `functools.cache` and calling it via `asyncio.to_thread`. This ensures the first access is offloaded and subsequent accesses are non-blocking cache hits.
**Action:** Implemented cached synchronous reader for documentation in `help_tool.py`.
