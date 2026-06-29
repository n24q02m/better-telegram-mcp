## 2025-05-15 - Concurrent Session Revocation
**Learning:** Sequential async calls for disconnecting multiple backends (e.g., Telethon clients) can cause significant delays because each disconnect involves an MTProto roundtrip. Using `asyncio.gather` reduces this latency to a single roundtrip.
**Action:** Always use `asyncio.gather` when performing bulk operations that involve network I/O or other awaitable tasks, especially for cleanup or shutdown procedures.
