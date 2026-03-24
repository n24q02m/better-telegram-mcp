
## 2026-03-24 - Async initialization non-blocking thread
**Learning:** `asyncio.to_thread` creates a background thread but if `await`ed, it still blocks the awaiting coroutine (e.g. an async generator like `_lifespan`). To execute synchronous IO-bound operations fully in the background without blocking the parent coroutine's progression, the thread task must be scheduled with `asyncio.create_task(asyncio.to_thread(...))`.
**Action:** Replaced `await asyncio.to_thread(webbrowser.open, _auth_url)` with a function wrapped in `asyncio.create_task(...)` inside the async lifespan initialization.
