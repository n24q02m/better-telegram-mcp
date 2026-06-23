## 2026-06-23 - [PERF] Synchronous DNS Resolution in Async Context
**Learning:** Calling synchronous, blocking DNS resolution functions like `socket.getaddrinfo` inside an asynchronous context blocks the main event loop, preventing other concurrent tasks from executing and degrading overall application performance.
**Action:** Always wrap blocking network or I/O operations (like DNS resolution or file system access) in `asyncio.to_thread()` when used within an `async` function to offload the work to a background thread and keep the event loop responsive.
