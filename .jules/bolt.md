## 2025-05-15 - Concurrent Session Revocation
**Learning:** Sequential async calls for disconnecting multiple backends (e.g., Telethon clients) can cause significant delays because each disconnect involves an MTProto roundtrip. Using `asyncio.gather` reduces this latency to a single roundtrip.
**Action:** Always use `asyncio.gather` when performing bulk operations that involve network I/O or other awaitable tasks, especially for cleanup or shutdown procedures.
## 2025-06-30 - Parallel KV Session Store Loading
**Learning:** `load_all` on a credential backend with individual `load()` operations suffers from an N+1 query bottleneck. Since the underlying PBKDF2 key derivations using the `cryptography` library release the GIL, thread pools provide significant speedups even in Python, overlapping both I/O and heavy crypto compute.
**Action:** Parallelize bulk load operations over single-item APIs using `ThreadPoolExecutor.map()` to avoid sequential blocking. Combine results with `zip(..., strict=True)`.
