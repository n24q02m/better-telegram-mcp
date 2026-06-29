## 2025-05-15 - Concurrent Session Revocation
**Learning:** Sequential async calls for disconnecting multiple backends (e.g., Telethon clients) can cause significant delays because each disconnect involves an MTProto roundtrip. Using `asyncio.gather` reduces this latency to a single roundtrip.
**Action:** Always use `asyncio.gather` when performing bulk operations that involve network I/O or other awaitable tasks, especially for cleanup or shutdown procedures.
## 2025-06-29 - Parallel KV Store Session Restoration
**Learning:** In scenarios with multiple active users, loading all session metadata via `KvSessionStore.load_all()` sequentially introduces an N+1 query bottleneck. Because mcp-core `PerPluginStore` uses PBKDF2 derivations (which release the GIL in the `cryptography` library), this loop is highly inefficient.
**Action:** Use `concurrent.futures.ThreadPoolExecutor.map()` alongside `zip(..., strict=True)` to parallelize independent backend load calls, drastically reducing I/O wait times and PBKDF2 bottlenecks.
