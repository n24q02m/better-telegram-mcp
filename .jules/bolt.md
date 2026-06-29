## 2025-05-22 - Asynchronous I/O Offloading in UserBackend
**Learning:** Refactoring internal helper methods that perform blocking filesystem I/O (e.g., `os.open`, `Path.mkdir`, `os.chmod`) to be `async def` and internalizing the thread offloading with `await asyncio.to_thread()` improves API clarity and ensures non-blocking behavior.
**Action:** In asynchronous backends, prefer `async def` for I/O helpers and use `await asyncio.to_thread()` internally.
