## 2026-06-23 - Async File Operations for Crypto Secrets
**Learning:** Synchronous file operations like `os.urandom().hex()` and atomic writes can block the asyncio event loop during critical auth phases.
**Action:** Always provide asynchronous alternatives using `asyncio.to_thread` for blocking I/O and CPU-bound crypto tasks (like generating large random secrets) to maintain responsiveness.
