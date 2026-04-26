## 2024-05-18 - Rate Limit Pruning Performance
**Learning:** For rate-limiting or sliding-window timestamp pruning where a list is strictly chronologically ordered (e.g. from `time.time()` appends in a single thread), rebuilding the list with a list comprehension (`[t for t in list if t > start]`) is an unnecessary O(N) operation and memory allocation.
**Action:** Use `bisect.bisect_right(list, start)` to find the cutoff index in O(log N) time, then perform an in-place C-level slice deletion (`del list[:idx]`). This prevents redundant memory allocation and speeds up pruning significantly.
